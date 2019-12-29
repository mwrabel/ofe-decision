# Import
from flask import Flask, render_template, redirect, request, url_for
import requests, os
from zus_czy_ike import Pension
import numpy as np
import pandas as pd
# Define app and set Secret Key
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# TODO feedback


# Index & input
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/wynik', methods=['POST'])
def wynik():
    r = float(request.form.get('r').replace(',', '.'))/100
    inflacja = float(request.form.get('inflacja').replace(',', '.'))/100
    prognozowana_emerytura_brutto = float(request.form.get('prognozowana_emerytura_brutto').replace(',', '.'))
    ofe = float(request.form.get('ofe').replace(',', '.'))
    kobieta = int(request.form.get('kobieta'))
    wiek = int(request.form.get('wiek'))

    pension = Pension(r=r,
                      inflacja=inflacja,
                      prognozowana_emerytura_brutto=prognozowana_emerytura_brutto,
                      ofe=ofe,
                      kobieta=kobieta,
                      wiek=wiek)
    pension.main()

    suma_dodatku_od_zus = str(np.round(pension.suma_dodatku_od_zus, 2))
    suma_dodatku_od_ike = str(np.round(pension.suma_dodatku_od_ike, 2))

    return render_template('wynik.html',
                           suma_dodatku_od_zus=suma_dodatku_od_zus,
                           suma_dodatku_od_ike=suma_dodatku_od_ike)


if __name__ == '__main__':
    app.run(ssl_context='adhoc', debug=True)
