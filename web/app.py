from flask import Flask, Response
import psycopg2, os, json

app = Flask(__name__)

DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_NAME = os.environ['DB_NAME']

db = psycopg2.connect(host=DB_HOST,
                      dbname=DB_NAME,
                      user=DB_USER,
                      password=DB_PASS)

@app.route("/api/trump")
def trump():
    cur = db.cursor()
    cur.execute("SELECT (t,v) FROM trump ORDER BY id DESC")    
    result = [[row[0], row[1]] for row in [eval(row[0]) for row in cur.fetchall()]]
    return Response(json.dumps(result), mimetype="application/json")
