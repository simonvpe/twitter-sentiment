from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from flask_sqlalchemy import SQLAlchemy

import os, datetime, dateparser, iso8601


app = FlaskAPI(__name__)

DB_PATH      = os.environ['DB_PATH']
DEFAULT_FROM = os.environ['DEFAULT_FROM']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(DB_PATH) + 'db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db  = SQLAlchemy(app)

class Sentiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime)
    value = db.Column(db.Float)
    tweet_count = db.Column(db.Integer)
    standard_deviation = db.Column(db.Float)
    
    def __init__(self, key, timestamp, value, tweet_count, standard_deviation):
        self.key = key
        self.timestamp = timestamp
        self.value = value
        self.tweet_count = tweet_count
        self.standard_deviation = standard_deviation

@app.route("/api/<string:table>", methods=["GET", "POST"], strict_slashes=False)

def list(table):
    if request.method == "GET":
        from_setting = str(request.args.get("from", DEFAULT_FROM))
        
        start = dateparser.parse(from_setting)
        start = start.replace(microsecond=0)

        now = datetime.datetime.now()
        now = now.replace(microsecond=0)
        
        records = Sentiment.query.filter_by(key=table).filter(Sentiment.timestamp >= start).all()
        return {
            "docType": "jts",
            "version": "1.0",
            "header": {
                "startTime": start.isoformat(),
                "endTime": now.isoformat(),
                "recordCount": len(records)
            },
            "data": [
                {
                    "timestamp": record.timestamp.isoformat(),
                    "value": record.value,
                    "standardDeviation": record.standard_deviation,
                    "tweetCount": record.tweet_count
                }
                for record in records
            ]
        }

    if request.method == "POST":
        value              = float(request.data.get('value', ''))
        time               = str(request.data.get('timestamp', ''))
        tweet_count        = int(request.data.get('tweet_count', ''))
        standard_deviation = float(request.data.get("standard_deviation", ''))
        record = Sentiment(table, iso8601.parse_date(time), value, tweet_count, standard_deviation)
        db.session.add(record)
        db.session.commit()
        return {
            "timestamp": record.timestamp.isoformat(),
            "key": record.key,
            "value": record.value,
            "standardDeviation": record.standard_deviation,
            "tweet_count": record.tweet_count
        }, 201

db.create_all()
