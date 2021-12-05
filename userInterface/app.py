"""
Routes and views for the flask application.
"""

import mysql.connector
from datetime import datetime
from os import environ

from flask import Flask
from flask import render_template

app = Flask(__name__)

mydb = mysql.connector.connect(
    host=environ.get("MYSQL_HOST", "localhost"),
    user=environ.get("MYSQL_USER", "root"),
    password=environ.get("MYSQL_PASSWORD", "mysecretpw"),
    database=environ.get("MYSQL_DATABASE", "prices"),
)

@app.route('/')
@app.route('/home')
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

def fetchResult():
    cur = mydb.cursor(dictionary=True)
    cur.execute("SELECT * FROM fuel_prices")

    return cur.fetchone()

@app.route('/result')
def result():
    """Renders the result page."""
    # Was vom Nutzer eingegeben wird
    parameters = [
        {"kraftstoff": "Diesel", "wochentag": "dienstags", "zeitfenster": "8 Uhr - 12 Uhr"}
    ]

    res = fetchResult()

    # Was als Ergebnis geliefert wird
    results = [
        {"name": "Esso Tankstelle", "street": "SCHOZACHER STR. 51", "plz": "70437", "city": "STUTTGART",
         "price": res["e5"]}
    ]

    return render_template(
        'result.html',
        title='Ergebnis',
        year=datetime.now().year,
        message='Das ist die günstigste Tankstelle',
        results=results,
        parameters=parameters
    )


if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
