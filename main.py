import os
import uuid
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 🔐 Claves directamente en el código (solo para pruebas locales o en Render)
API_KEY = "bg_68c52d41350e2c3fff36daec2388c935"
API_SECRET = "975a43e9534e30c7e43493c1e74a4eb74c1a6a394af445211f48cc5196471bd7"
API_PASS = "170514LCSDx"

BASE_URL = "https://api.bitget.com"

headers = {
    "ACCESS-KEY": API_KEY,
    "ACCESS-SIGN": "",
    "ACCESS-TIMESTAMP": "",
    "ACCESS-PASSPHRASE": API_PASS,
    "Content-Type": "application/json"
}

# 🔧 Parámetros por defecto
MARGIN_COIN = "USDT"
SYMBOL = "SOLUSDT"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"📨 Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol")

    if not signal or not symbol:
        return "Faltan datos", 400

    print(f"✅ Símbolo recibido: {symbol}")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        return send_order(symbol, "open_long")

    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        return send_order(symbol, "open_short")

    elif signal == "EXIT_CONFIRMED":
        print("🔄 Señal de cierre recibida.")
        return close_position(symbol)

    elif signal == "LIST_POSITIONS":
        return list_positions()

    return "Señal no válida", 400

def send_order(symbol, side):
    url = f"{BASE_URL}/api/mix/v1/order/placeOrder"
    body = {
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "size": "1",
        "price": "0",
        "side": "buy" if side == "open_long" else "sell",
        "orderType": "market",
        "positionSide": side.split("_")[1],
        "clientOid": str(uuid.uuid4())
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    print(f"🟢 ORDEN {body['side'].upper()} → {response.status_code}, {response.text}")
    return jsonify(success=True)

def close_position(symbol):
    endpoint = f"/api/mix/v1/position/singlePosition?symbol={symbol}&marginCoin={MARGIN_COIN}"
    url = BASE_URL + endpoint
    print(f"📡 Llamando a endpoint: {endpoint}")

    response = requests.get(url, headers=headers)
    try:
        position_data = response.json().get("data")
    except Exception as e:
        print(f"❌ Error interpretando posición: {e}")
        return jsonify(success=False), 500

    if not position_data:
        print("❌ No hay posición abierta.")
        return jsonify(success=False), 400

    side = position_data.get("holdSide")
    if side == "long":
        return send_order(symbol, "close_long")
    elif side == "short":
        return send_order(symbol, "close_short")
    else:
        print("❌ No se reconoce el lado de la posición.")
        return jsonify(success=False), 400

def list_positions():
    endpoint = "/api/mix/v1/position/allPosition"
    url = BASE_URL + endpoint

    response = requests.get(url, headers=headers)
    print(f"📋 Posiciones abiertas (status {response.status_code}): {response.text}")
    return jsonify(success=response.ok)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
