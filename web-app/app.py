"""
Routes and views for the flask application.
"""

import mysql.connector
from datetime import datetime
from datetime import timedelta
from os import environ
import pandas as pd
from io import BytesIO
from matplotlib.figure import Figure
from flask import Flask, render_template, request
import base64

app = Flask(__name__)

mydb = mysql.connector.connect(
    host=environ.get("MYSQL_HOST", "localhost"),
    user=environ.get("MYSQL_USER", "root"),
    password=environ.get("MYSQL_PASSWORD", "mysecretpw"),
    database=environ.get("MYSQL_DATABASE", "prices"),
)


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
    # Was der Benutzer eingegeben hat
    req = request.args
    parameters = [
        {"kraftstoff": req["kraftstoff"], "wochentag": req["zeit"]}
    ]
    # Was als Ergebnis geliefert wird
    res = pd.DataFrame(fetchResult(req["plz"]))
    results = [{"name": "Esso Tankstelle", "street": "SCHOZACHER STR. 51", "plz": req["plz"], "city": "STUTTGART",
                "price": res[req["kraftstoff"]]}
               ]

    # Generate the figure
    fig = Figure(figsize=(12, 6), dpi=80)
    ax = fig.subplots()
    ax.plot(res["window_start"], res[req["kraftstoff"]],label=req["kraftstoff"].title())
    ax.legend(loc="upper left")
    ax.grid()
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png",transparent=True)
    # Embed the result in the html output.
    plot_url = base64.b64encode(buf.getbuffer()).decode("ascii")

    return render_template(
        'result.html',
        title='Ergebnis',
        year=datetime.now().year,
        message=f'Der Preisverlauf für {req["kraftstoff"].title()} über die letzten 7 Tage:',
        results=results,
        parameters=parameters,
        plot_url=plot_url)


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
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
