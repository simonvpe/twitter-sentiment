from flask import Flask, Response, request
from flask_api import FlaskAPI, exceptions
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psycopg2, os, json
from psycopg2 import sql

app = FlaskAPI(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_NAME = os.environ['DB_NAME']

db = psycopg2.connect(host=DB_HOST,
                      dbname=DB_NAME,
                      user=DB_USER,
                      password=DB_PASS)

@app.route("/api/<string:table>/")
def list(table):
    cur = db.cursor()
    try:
        cur.execute(sql.SQL("SELECT (t,v) FROM {} ORDER BY id DESC").format(sql.Identifier(table)))  
    except:
        db.rollback()
        raise exceptions.NotFound()
    return [[row[0], row[1]] for row in [eval(row[0]) for row in cur.fetchall()]]
