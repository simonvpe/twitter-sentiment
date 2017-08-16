from collections import Sequence
import re, tflearn, os, sys, argparse, traceback
import tweepy, tensorflow as tf
import numpy as np
import datetime
from tflearn.data_utils import VocabularyProcessor
import dateparser
import time
import pandas as pd
from influxdb import InfluxDBClient

parser = argparse.ArgumentParser(description="Perform sentiment analysis and insert results in database")
parser.add_argument("terms", nargs="+", help="The search terms")

args=vars(parser.parse_args())

TWITTER_CONSUMER_KEY        = os.environ['TWITTER_CONSUMER_KEY']
TWITTER_CONSUMER_SECRET     = os.environ['TWITTER_CONSUMER_SECRET']
TWITTER_ACCESS_TOKEN        = os.environ['TWITTER_ACCESS_TOKEN']
TWITTER_ACCESS_TOKEN_SECRET = os.environ['TWITTER_ACCESS_TOKEN_SECRET']
MODEL                       = os.environ['MODEL']
VOCAB                       = os.environ['VOCAB']

users = set([user[1:] for user in filter(lambda x: x[0] == '@',args["terms"])])

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

# Open connection to influxdb
client = InfluxDBClient('influxdb', 8086, 'root', 'root', 'db')
client.create_database('db')

client.create_retention_policy('one_hour',  '1h',   1, 'db', True)
client.create_retention_policy('one_week',  '7d',   1, 'db')
client.create_retention_policy('one_month', '31d',  1, 'db')
client.create_retention_policy('forever',   'INF',  1, 'db')

def cq_query(functions, destination_measurement, measurement, interval, tag_keys, where = ""):
    q = ['SELECT ', functions, ' INTO ', destination_measurement,' FROM ', measurement]

    if where and len(where) > 0:
        q += [' WHERE ', where]

    q += [' GROUP BY ' + 'time(' + interval + ')']

    if tag_keys and len(tag_keys) > 0:
        q += [',', tag_keys]
                        
    return ''.join(q)
    
def create_cq_query(cq_name, database_name, query):
    return 'CREATE CONTINUOUS QUERY ' + cq_name + ' ON ' + database_name + ' BEGIN ' + query + ' END'

try:
    client.query(
        create_cq_query('cq_1m', 'db',
                        cq_query(
                            functions='mean(sentiment) AS sentiment, stddev(sentiment) AS std, count(sentiment) AS tweets',
                            destination_measurement='"one_hour"."sentiment_1m"',
                            measurement='"one_hour"."sentiment"',
                            interval="1m",
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass

try:
    client.query(
        create_cq_query('cq_1m_top', 'db',
                        cq_query(
                            functions='top(sentiment,1), text, id',
                            destination_measurement='"forever"."top_sentiment"',
                            measurement='"one_hour"."sentiment"',
                            interval='1m',
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass

try:
    client.query(
        create_cq_query('cq_1m_bottom', 'db',
                        cq_query(
                            functions='bottom(sentiment,1), text, id',
                            destination_measurement='"forever"."bottom_sentiment"',
                            measurement='"one_hour"."sentiment"',
                            interval='1m',
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass


try:
    client.query(
        create_cq_query('cq_15m', 'db',
                        cq_query(
                            functions='mean(sentiment) AS sentiment, mean(std) AS std, sum(tweets) AS tweets',
                            destination_measurement='"one_week"."sentiment_15m"',
                            measurement='"one_hour"."sentiment_1m"',
                            interval="15m",
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass

try:
    client.query(
        create_cq_query('cq_1h', 'db',
                        cq_query(
                            functions='mean(sentiment) AS sentiment, mean(std) AS std, sum(tweets) AS tweets',
                            destination_measurement='"one_month"."sentiment_1h"',
                            measurement='"one_week"."sentiment_15m"',
                            interval="1h",
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass

try:
    client.query(
        create_cq_query('cq_1d', 'db',
                        cq_query(
                            functions='mean(sentiment) AS sentiment, mean(std) AS std, sum(tweets) AS tweets',
                            destination_measurement='"forever"."sentiment_1d"',
                            measurement='"one_month"."sentiment_1h"',
                            interval="1d",
                            tag_keys='"key"'
                        )
        )
    )
except:
    pass
    
# Start listening
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

class MyStreamListener(tweepy.StreamListener):
    sent = SentimentLookup()
    wait_duration_s = 60
    counter = 0
    
    def on_status(self, status):
        try:
            MyStreamListener.wait_duration_s = 60
            
            author = status.user.screen_name.encode('utf-8', errors='ignore')
            text = status.text.encode('utf-8', errors='ignore')
            sentiment = MyStreamListener.sent.sentiment(text)
            mentions = set([m['screen_name'] for m in status.entities['user_mentions']])
            
            # Whenever a user was mentioned
            for user in users.intersection(mentions):
                client.write_points([{
                    "measurement":   "sentiment",
                    "time":          status.created_at.isoformat(),
                    "tags": {
                        "key":       '@'+user,
                        # This counter is needed to make points with the same
                        # timestamp unique
                        "counter":   MyStreamListener.counter
                    },
                    "fields": {
                        "sentiment": sentiment,
                        "text":      text,
                        "author":    author
                    }
                }], retention_policy="one_hour")
                MyStreamListener.counter += 1

            # Whenever a user tweeted
            if author in users:
                client.write_points([{
                    "measurement": "tweet",
                    "time":        status.created_at.isoformat(),
                    "tags": {
                        "key":     '@'+author,
                        "counter": MyStreamListener.counter
                    },
                    "fields": {
                        "sentiment": sentiment,
                        "text":      text
                    }
                }], retention_policy="forever")
                MyStreamListener.counter += 1
        except:
            print("Exception in user code")
            print('-'*60)
            traceback.print_exc()
            raise
            
        
    def on_error(self, status_code):
        if status_code == 420:
            print("Error 420: Waiting for %d seconds" % MyStreamListener.wait_duration_s)
            # Initially wait one minute, subsequent fails doubles that time
            time.sleep(MyStreamListener.wait_duration_s)
            MyStreamListener.wait_duration_s = MyStreamListener.wait_duration_s * 2
            return True
        raise Exception(str(status_code))
    
stream = tweepy.Stream(auth = api.auth, listener=MyStreamListener())
stream.filter(track=args["terms"], async=False, languages=['en'])
