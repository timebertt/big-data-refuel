"""
Routes and views for the flask application.
"""

import mysql.connector
from datetime import datetime
from os import environ

from flask import Flask, render_template, request

app = Flask(__name__)

mydb = mysql.connector.connect(
    host=environ.get("MYSQL_HOST", "localhost"),
    user=environ.get("MYSQL_USER", "root"),
    password=environ.get("MYSQL_PASSWORD", "mysecretpw"),
    database=environ.get("MYSQL_DATABASE", "prices"),
)

def fetchResult():
    cur = mydb.cursor(dictionary=True)
    cur.execute("SELECT * FROM fuel_prices")

    return cur.fetchone()

@app.route('/',methods=["GET", "POST"])
@app.route('/home',methods=["GET", "POST"])
def home():
    """Renders the home page."""

    if request.method == "POST":
        # Was der Benutzer eingegeben hat
        req = request.form
        parameters = [
            {"kraftstoff": req["kraftstoff"], "wochentag": req["zeit"]}
        ]

        # Was als Ergebnis geliefert wird
        res = fetchResult()
        results = [
            {"name": "Esso Tankstelle", "street": "SCHOZACHER STR. 51", "plz": res["post_code"], "city": "STUTTGART",
            "price": res["e5"]}
        ]

        return render_template(
            'result.html',
            title='Ergebnis',
            year=datetime.now().year,
            message='Das ist die günstigste Tankstelle',
            results=results,
            parameters=parameters)

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
