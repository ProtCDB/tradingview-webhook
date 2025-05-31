from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import os
import requests
import json

app = Flask(__name__)

# === VARIABLES DE ENTORNO ===
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
SYMBOL = "SOLUSDT"
MARGIN_COIN = "USDT"

# === FUNCIONES DE FIRMA Y CABECERAS ===
def sign(method, path, timestamp, body=''):
    pre_sign = f"{timestamp}{method.upper()}{path}{body}"
    signature = hmac.new(API_SECRET.encode(), pre_sign.encode(), hashlib.sha256).hexdigest()
    return signature

def headers(method, path, body=''):
    timestamp = str(int(time.time() * 1000))
    signature = sign(method, path, timestamp, body)
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

# === ORDENES BITGET ===
def close_all_positions():
    url = f"{BASE_URL}/api/mix/v1/position/close-position"
    body = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN,
        "holdSide": "long"  # primero long
    }
    requests.post(url, headers=headers("POST", "/api/mix/v1/position/close-position", json.dumps(body)), json=body)
    body["holdSide"] = "short"  # luego short
    requests.post(url, headers("POST", "/api/mix/v1/position/close-position", json.dumps(body)), json=body)

def place_order(side):
    url = f"{BASE_URL}/api/mix/v1/order/place-order"
    order = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "0.1"  # puedes ajustar el tamaño
    }
    response = requests.post(url, headers=headers("POST", "/api/mix/v1/order/place-order", json.dumps(order)), json=order)
    return response.text

# === WEBHOOK DE TRADINGVIEW ===
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    signal = data.get("signal", "").upper()

    print(f"🚨 Señal recibida: {signal}")

    if signal == "ENTRY_LONG":
        close_all_positions()
        place_order("open_long")

    elif signal == "ENTRY_SHORT":
        close_all_positions()
        place_order("open_short")

    elif signal == "EXIT_LONG_SL" or signal == "EXIT_LONG_TP":
        place_order("close_long")

    elif signal == "EXIT_SHORT_SL" or signal == "EXIT_SHORT_TP":
        place_order("close_short")

    elif signal == "EXIT_CONFIRMED":
        close_all_positions()

    else:
        print("❓ Señal no reconocida.")
        return jsonify({"error": "Señal no reconocida"}), 400

    return jsonify({"status": "ok"}), 200

# === INICIO DEL SERVIDOR ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

