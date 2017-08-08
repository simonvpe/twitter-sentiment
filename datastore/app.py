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
    def __init__(self, key, timestamp, value):
        self.key = key
        self.timestamp = timestamp
        self.value = value

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
                    "value": record.value
                }
                for record in records
            ]
        }

    if request.method == "POST":
        value  = float(request.data.get('value', ''))
        time   = int(request.data.get('timestamp', ''))
        record = Sentiment(table, datetime.datetime.fromtimestamp(time), value)
        db.session.add(record)
        db.session.commit()
        return {
            "timestamp": record.timestamp,
            "key": record.key,
            "value": record.value
        }, 201

db.create_all()
