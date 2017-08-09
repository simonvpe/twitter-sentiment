from collections import Sequence
import re, tflearn, os, sys, argparse
import tweepy, tensorflow as tf
import numpy as np
import datetime
from tflearn.data_utils import VocabularyProcessor
import requests, json
import dateparser

parser = argparse.ArgumentParser(description="Perform sentiment analysis and insert results in database")
parser.add_argument("terms", nargs="+", help="The search terms")

args=vars(parser.parse_args())

PERIOD                      = os.environ['PERIOD']
MEAN_SENTIMENT_DATASTORE    = os.environ["MEAN_SENTIMENT_DATASTORE"]
TOP_TWEETS_DATASTORE        = os.environ["TOP_TWEETS_DATASTORE"]
WORST_TWEETS_DATASTORE      = os.environ["WORST_TWEETS_DATASTORE"]
KEY                         = os.environ["KEY"]
TWITTER_CONSUMER_KEY        = os.environ['TWITTER_CONSUMER_KEY']
TWITTER_CONSUMER_SECRET     = os.environ['TWITTER_CONSUMER_SECRET']
TWITTER_ACCESS_TOKEN        = os.environ['TWITTER_ACCESS_TOKEN']
TWITTER_ACCESS_TOKEN_SECRET = os.environ['TWITTER_ACCESS_TOKEN_SECRET']
MODEL                       = os.environ['MODEL']
VOCAB                       = os.environ['VOCAB']

class SentimentLookup:
    net = tflearn.input_data     ([None, 40])
    net = tflearn.embedding      (net, input_dim=12495, output_dim=128)
    net = tflearn.lstm           (net, 128, dropout=0.8)
    net = tflearn.fully_connected(net, 2, activation='softmax')
    net = tflearn.regression     (net, optimizer='adam', learning_rate=0.001,
                                       loss='categorical_crossentropy')
    model = tflearn.DNN(net, tensorboard_verbose=0)
    model.load(MODEL)

    vp = VocabularyProcessor.restore(VOCAB)
    
    def _process_tweet(self, tweet = ""):
        cleaned = str(tweet).upper()
        cleaned = re.sub('&\w+;',   '',          cleaned)
        cleaned = re.sub('\'',      '',          cleaned)
        cleaned = re.sub('@\w+ ',   'USERNAME ', cleaned)
        cleaned = re.sub('[^A-Z ]', '',          cleaned)
        cleaned = re.sub('[ ]+',    ' ',         cleaned)
        return cleaned.strip()

    def sentiment(self, data):
        if isinstance(data, str):
            query = [x for x in SentimentLookup.vp.transform([self._process_tweet(data)])]
            bad, good = SentimentLookup.model.predict(query).tolist()[0]
            return good

        data  = map(self._process_tweet, data)
        query = [x for x in SentimentLookup.vp.transform(data)]
        return SentimentLookup.model.predict(query)[:,1]

# Start listening
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

class MyStreamListener(tweepy.StreamListener):
    sent = SentimentLookup()
    buf  = []
    last = datetime.datetime.now()
    
    def on_status(self, status):
        tweet = status.text.encode('utf-8', errors='ignore')
        MyStreamListener.buf.append((status.created_at, MyStreamListener.sent.sentiment(tweet), status.text))
        
        # Commit from time to time
        if dateparser.parse(PERIOD + ' ago') >= MyStreamListener.last:
            arr = np.array(MyStreamListener.buf)

            sentiments  = arr[:,1]
            timestamps  = map(lambda t: int(t.strftime("%s")), arr[:,0])
            epoch       = int(np.mean(timestamps))
            value       = np.mean(sentiments)
            std         = np.std(sentiments)
            tweet_count = len(sentiments)

            # Send to mean-sentiment-datastore
            data     = json.dumps({
                "timestamp": datetime.datetime.fromtimestamp(epoch).isoformat(),
                "value": value,
                "standard_deviation": std,
                "tweet_count": tweet_count
            })
            url      = 'http://%s/api/mean-sentiment/%s' % (MEAN_SENTIMENT_DATASTORE, KEY)
            headers  = {'Content-Type': 'application/json'}
            response = requests.post(url, data=data, headers=headers)

            # Send to top-tweets-datastore
            texts = arr[:,2]
            top_idx = np.argmax(sentiments)
            top_sentiment = sentiments[top_idx]
            top_timestamp = timestamps[top_idx]
            top_text      = texts[top_idx]

            data = json.dumps({
                "timestamp": datetime.datetime.fromtimestamp(top_timestamp).isoformat(),
                "sentiment": top_sentiment,
                "text": top_text
            })
            url      = 'http://%s/api/top-tweets/%s' % (TOP_TWEETS_DATASTORE, KEY)
            headers  = {'Content-Type': 'application/json'}
            response = requests.post(url, data=data, headers=headers)

            # Send to worst-tweets-datastore
            texts = arr[:,2]
            worst_idx = np.argmin(sentiments)
            worst_sentiment = sentiments[worst_idx]
            worst_timestamp = timestamps[worst_idx]
            worst_text      = texts[worst_idx]

            response = requests.post(
                'http://%s/api/worst-tweets/%s' % (WORST_TWEETS_DATASTORE, KEY),
                data = json.dumps({
                    "timestamp": datetime.datetime.fromtimestamp(worst_timestamp).isoformat(),
                    "sentiment": worst_sentiment,
                    "text": worst_text
                }),
                headers = {
                    'Content-Type': 'application/json'
                }
            )
            
            MyStreamListener.buf = []
            MyStreamListener.last = datetime.datetime.now()
        
    def on_error(self, status_code):
        raise Exception(str(status_code))
    
stream = tweepy.Stream(auth = api.auth, listener=MyStreamListener())
stream.filter(track=args["terms"], async=False, languages=['en'])
