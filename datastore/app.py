from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

import os, datetime


app = FlaskAPI(__name__)

DB_PATH  = os.environ['DB_PATH']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(DB_PATH)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db  = SQLAlchemy(app)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


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
        records = Sentiment.query.filter_by(key=table).all()
        return {
            "docType": "jts",
            "version": "1.0",
            "data": [
                {
                    "timestamp": record.timestamp,
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
