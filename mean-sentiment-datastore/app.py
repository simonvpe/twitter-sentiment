from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from influxdb import InfluxDBClient
import os, datetime, dateparser, iso8601


app = FlaskAPI(__name__)

DB_PATH            = os.environ['DB_PATH']
DEFAULT_RESOLUTION = os.environ['DEFAULT_RESOLUTION']

# Open connection to influxdb
client = InfluxDBClient('influxdb', 8086, 'root', 'root', 'db')

@app.route("/api/mean-sentiment", strict_slashes=False)
def list():
    res = str(request.args.get("res", DEFAULT_RESOLUTION))

    if res == 'hour':
        return client.query('SELECT * FROM "one_hour"."sentiment_1m" WHERE time > now() - 1h GROUP BY "key"').raw

    if res == 'week':
        return client.query('SELECT * FROM "one_week"."sentiment_15m" WHERE time > now() - 7d GROUP BY "key"').raw

    if res == 'month':
        return client.query('SELECT * FROM "one_month"."sentiment_1h" WHERE time > now() - 30d GROUP BY "key"').raw

    if res == 'year':
        return client.query('SELECT * FROM "forever"."sentiment_1d" WHERE time > now() - 365d GROUP BY "key"').raw
        
