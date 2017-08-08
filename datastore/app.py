from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from flask_sqlalchemy import SQLAlchemy

import os, datetime, dateparser


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
    def __init__(self, key, timestamp, value, tweet_count):
        self.key = key
        self.timestamp = timestamp
        self.value = value
        self.tweet_count = tweet_count

@app.route("/api/<string:table>", methods=["GET", "POST"], strict_slashes=False)

def list(table):
    if request.method == "GET":
        from_setting = str(request.args.get("from", DEFAULT_FROM))
        start = dateparser.parse(from_setting)
        records = Sentiment.query.filter_by(key=table).filter(Sentiment.timestamp >= start).all()
        return {
            "docType": "jts",
            "version": "1.0",
            "header": {
                "startTime": start.isoformat(),
                "endTime": datetime.datetime.now().isoformat(),
                "recordCount": len(records)
            },
            "data": [
                {
                    "timestamp": record.timestamp.isoformat(),
                    "value": record.value,
                    "tweetCount": record.tweet_count
                }
                for record in records
            ]
        }

    if request.method == "POST":
        value       = float(request.data.get('value', ''))
        time        = int(request.data.get('timestamp', ''))
        tweet_count = int(request.data.get('tweet_count', ''))
        record = Sentiment(table, datetime.datetime.fromtimestamp(time), value, tweet_count)
        db.session.add(record)
        db.session.commit()
        return {
            "timestamp": record.timestamp.isoformat(),
            "key": record.key,
            "value": record.value,
            "tweet_count": record.tweet_count
        }, 201

db.create_all()
