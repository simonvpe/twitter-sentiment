from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from flask_sqlalchemy import SQLAlchemy

import os, datetime, dateparser, iso8601


app = FlaskAPI(__name__)

DB_PATH      = os.environ['DB_PATH']
DEFAULT_FROM = os.environ['DEFAULT_FROM']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(DB_PATH + '/top-tweets-db.sqlite') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db  = SQLAlchemy(app)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime)
    sentiment = db.Column(db.Float)
    text = db.Column(db.String(140))
    
    def __init__(self, key, timestamp, sentiment, text):
        self.key = key
        self.timestamp = timestamp
        self.sentiment = sentiment
        self.text = text

@app.route("/api/top-tweets/<string:table>", methods=["GET", "POST"], strict_slashes=False)
def list(table):
    if request.method == "GET":
        from_setting = str(request.args.get("from", DEFAULT_FROM))
        
        start = dateparser.parse(from_setting)
        start = start.replace(microsecond=0)

        now = datetime.datetime.now()
        now = now.replace(microsecond=0)
        
        records = Record.query.filter_by(key=table).filter(Record.timestamp >= start).all()
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
                    "sentiment": record.sentiment,
                    "text": record.text
                }
                for record in records
            ]
        }

    if request.method == "POST":
        sentiment          = float(request.data.get('sentiment', ''))
        time               = str(request.data.get('timestamp', ''))
        text               = str(request.data.get('text', ''))
        record = Record(table, iso8601.parse_date(time), sentiment, text)
        db.session.add(record)
        db.session.commit()
        return {
            "timestamp": record.timestamp.isoformat(),
            "key": record.key,
            "sentiment": record.sentiment,
            "text": record.text
        }, 201

db.create_all()
