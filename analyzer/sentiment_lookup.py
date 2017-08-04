from collections import Sequence
import re, tflearn, os, sys, argparse, psycopg2, tweepy, tensorflow as tf, numpy as np
import datetime
from tflearn.data_utils import VocabularyProcessor

parser = argparse.ArgumentParser(description="Perform sentiment analysis and insert results in database")
parser.add_argument("dbhost",     help="The pgsql host")
parser.add_argument("dbuser",     help="The pgsql user")
parser.add_argument("dbpassword", help="The pgsql password")
parser.add_argument("dbname",     help="The pgsql database name")
parser.add_argument("dbtable",    help="The pgsql table")
parser.add_argument("terms", nargs="+", help="The search terms")

print(sys.argv)
args=vars(parser.parse_args())


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
        cleaned = tweet.upper()
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

# Connect to database    
db = psycopg2.connect(host=args["dbhost"],
                      dbname=args["dbname"],
                      user=args["dbuser"],
                      password=args["dbpassword"])

# Create table
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS %s (id serial, t timestamp, v real, PRIMARY KEY(id));" %
            args["dbtable"])
db.commit()

# Start listening
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

class MyStreamListener(tweepy.StreamListener):
    sent = SentimentLookup()
    buf = []
    
    def on_status(self, status):
        tweet = status.text.encode('utf-8', errors='ignore')
        MyStreamListener.buf.append((status.created_at, MyStreamListener.sent.sentiment(tweet)))

        # Commit from time to time
        if len(MyStreamListener.buf) == 1000:
            arr = np.array(MyStreamListener.buf)
            epoch = int(np.mean(map(lambda t: int(t.strftime("%s")), arr[:,0])))
            time  = datetime.datetime.fromtimestamp(epoch)
            value = np.mean(arr[:,1])
            
            cur = db.cursor()
            tbl = args["dbtable"]
            cur.execute("INSERT INTO %s (t,v) VALUES ('%s',%f)" % (tbl,time,value))
            db.commit()

            MyStreamListener.buf = []
        
    def on_error(self, status_code):
        raise Exception(str(status_code))
    
stream = tweepy.Stream(auth = api.auth, listener=MyStreamListener())
stream.filter(track=args["terms"], async=False)
