"""
Routes and views for the flask application.
"""
import base64
import socket
import time
from datetime import datetime, timedelta
from io import BytesIO
from os import environ

import mysql.connector
import numpy as np
import pandas as pd
import sched
from flask import Flask, render_template, request
from geopy.geocoders import Nominatim
from matplotlib.figure import Figure
from pymemcache.client.hash import HashClient

app = Flask(__name__)

# MySQL connection
mydb = mysql.connector.connect(
    host=environ.get("MYSQL_HOST", "localhost"),
    user=environ.get("MYSQL_USER", "root"),
    password=environ.get("MYSQL_PASSWORD", "mysecretpw"),
    database=environ.get("MYSQL_DATABASE", "prices"),
)

# memcached connection
memcachedOptions = {
    "host": environ.get("MEMCACHED_HOST", "localhost"),
    "port": int(environ.get("MEMCACHED_PORT", "11211")),
    "refreshInterval": int(environ.get("MEMCACHED_REFRESH_INTERVAL", "10")),
}

memcacheClient = None
memcachedServers = []


def initMemcacheClient():
    global memcacheClient, memcachedServers

    try:
        serversLookup = [a[4] for a in socket.getaddrinfo(memcachedOptions["host"], memcachedOptions["port"],
                                                          proto=socket.IPPROTO_TCP)]
    except socket.gaierror as e:
        memcachedServers = []
        print(f"Error getting memcached servers from DNS: {e}")
        return

    serversLookup.sort()
    if np.array_equal(serversLookup, memcachedServers):
        return

    memcachedServers = serversLookup
    print(f"Updated memcached server list to {memcachedServers}")

    if memcacheClient is not None:
        # disconnect existing client
        memcacheClient.close()

    memcacheClient = HashClient(memcachedServers)


initMemcacheClient()

s = sched.scheduler(time.time, time.sleep)


def refreshMemcacheClient(sc):
    initMemcacheClient()
    s.enter(memcachedOptions["refreshInterval"], 1, refreshMemcacheClient, (sc,))


s.enter(memcachedOptions["refreshInterval"], 1, refreshMemcacheClient, (s,))
s.run()

def fetchResultFromCache(post_code):
    if memcacheClient is None:
        return None

    return memcacheClient.get(f'/prices/{post_code}')

def fetchResult(input_post_code):
    # Rufe nur die Werte der letzten 7 Tage ab
    # today = datetime.today()
    today = datetime(2021, 11, 15, 12, 0, 0)
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur = mydb.cursor(dictionary=True, buffered=True)
    cur.execute("""
        SELECT * FROM fuel_prices
        WHERE post_code = %s AND window_start > %s AND window_start < %s
        """, (input_post_code, start_date, today))
    return cur.fetchall()


@app.route('/result', methods=["GET"])
def result():
    # User input
    req = request.args

    # Query result
    post_code = req["plz"]
    result = fetchResultFromCache(post_code)
    if result is not None:
        print(f"cache hit for post code {post_code}")
    else:
        print(f"cache miss for post code {post_code}")
        result = fetchResult(post_code)
        memcacheClient.set(f'/prices/{post_code}', result)

    res = pd.DataFrame(result)

    # Generate the figure
    fig = Figure(figsize=(12, 6), dpi=80)
    ax = fig.subplots()
    ax.plot(res["window_start"], res[req["kraftstoff"]], label=req["kraftstoff"].title())
    ax.legend(loc="upper left")
    ax.grid()
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    # Embed the result in the html output.
    plot_url = base64.b64encode(buf.getbuffer()).decode("ascii")

    # Receive location information
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(req["plz"]).raw['display_name'].split()

    return render_template(
        'result.html',
        title='Ergebnis',
        year=datetime.now().year,
        message=f'Der Preisverlauf für {req["kraftstoff"].title()} über die letzten 7 Tage',
        plot_url=plot_url,
        location=location)


@app.route('/', methods=["GET"])
@app.route('/home', methods=["GET"])
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='Neue Suche',
        year=datetime.now().year,
    )


@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Kontakt',
        year=datetime.now().year,
        message='Hier stehen die Kontaktdaten'
    )


@app.route('/faq')
def faq():
    """Renders the faq page."""
    return render_template(
        'faq.html',
        title='FAQ',
        year=datetime.now().year,
        message='Hier findest du Antworten auf wichtige Fragen'
    )


if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', '0.0.0.0')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
