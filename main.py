import json
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
API_PASS = os.getenv('API_PASS')
BASE_URL = "https://api.bitget.com"

MARGIN_COIN = "USDT"
PRODUCT_TYPE = "USDT-FUTURES"  # Necesario para el endpoint de listar posiciones

# 🔐 Autenticación
def auth_headers(method, endpoint, body=""):
    timestamp = str(int(time.time() * 1000))
    pre_hash = f"{timestamp}{method.upper()}{endpoint}{body}"
    sign = hmac.new(API_SECRET.encode(), pre_hash.encode(), hashlib.sha256).hexdigest()
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASS,
        "Content-Type": "application/json"
    }

# 📋 Listar posiciones abiertas
def list_open_positions():
    endpoint = "/api/v2/mix/position/all-position"
    params = f"?productType={PRODUCT_TYPE}&marginCoin={MARGIN_COIN}"
    headers = auth_headers("GET", endpoint + params)
    resp = requests.get(BASE_URL + endpoint + params, headers=headers)
    print("📋 Posiciones abiertas (status {}): {}".format(resp.status_code, resp.text))
    return resp.json()

# 📩 Webhook receptor
@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("📨 Payload recibido:", data)

        signal = data.get('signal')
        symbol = data.get('symbol')

        if not signal or not symbol:
            return "Missing signal or symbol", 400

        print(f"✅ Símbolo recibido: {symbol}")

        if signal == "LIST_POSITIONS":
            response = list_open_positions()
            return jsonify(response)

        return "Señal no reconocida para este ejemplo.", 200

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        return "Error interno", 500

if __name__ == '__main__':
    app.run(debug=True)
