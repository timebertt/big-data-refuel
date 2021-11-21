"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from userInterface import app

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

@app.route('/result')
def result():
    """Renders the result page."""
    #Was vom Nutzer eingegeben wird
    parameters= [
        {"kraftstoff": "Diesel", "wochentag": "dienstags", "zeitfenster": "8 Uhr - 12 Uhr"}
        ]

    #Was als Ergebnis geliefert wird
    results= [
        {"name": "Esso Tankstelle", "street": "SCHOZACHER STR. 51", "plz": "70437", "city": "STUTTGART", "price": "1.299"}
        ]

    return render_template(
        'result.html',
        title='Ergebnis',
        year=datetime.now().year,
        message='Das ist die günstigste Tankstelle',
        results=results,
        parameters=parameters
    )
