import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

def auth_headers(method, endpoint, body=""):
    timestamp = str(int(time.time() * 1000))
    prehash = timestamp + method.upper() + endpoint + body
    sign = hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(sign).decode()
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def place_order(symbol, side):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated"
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🟢 ORDEN {side} → {resp.status_code}, {resp.text}")

def place_close_order(symbol, side, size):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "reduceOnly": True
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🔴 ORDEN CIERRE {side} → {resp.status_code}, {resp.text}")

def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    endpoint = f"/api/mix/v1/position/singlePosition?symbol={symbol}&marginCoin={MARGIN_COIN}"
    headers = auth_headers("GET", endpoint)
    resp = requests.get(BASE_URL + endpoint, headers=headers)
    print(f"📡 Llamando a endpoint: {endpoint}")
    if resp.status_code != 200:
        print(f"❌ Error al obtener posición: Status {resp.status_code} - {resp.text}")
        return

    data = resp.json().get("data")
    if not data:
        print("⚠️ No hay posición abierta para cerrar.")
        return

    try:
        # Dependiendo del formato, data puede ser lista o dict
        if isinstance(data, list):
            for position in data:
                long_pos = float(position.get("long", {}).get("available", 0))
                short_pos = float(position.get("short", {}).get("available", 0))
                if long_pos > 0:
                    print("🔴 Cerrando LONG...")
                    place_close_order(symbol, "SELL", long_pos)
                if short_pos > 0:
                    print("🔴 Cerrando SHORT...")
                    place_close_order(symbol, "BUY", short_pos)
        else:
            long_pos = float(data.get("long", {}).get("available", 0))
            short_pos = float(data.get("short", {}).get("available", 0))
            if long_pos > 0:
                print("🔴 Cerrando LONG...")
                place_close_order(symbol, "SELL", long_pos)
            if short_pos > 0:
                print("🔴 Cerrando SHORT...")
                place_close_order(symbol, "BUY", short_pos)
    except Exception as e:
        print("❌ Error interpretando posición:", str(e))

def list_open_positions():
    endpoint = "/api/mix/v1/position/openPositions"
    headers = auth_headers("GET", endpoint)
    resp = requests.get(BASE_URL + endpoint, headers=headers)
    print("📋 Posiciones abiertas (status {}): {}".format(resp.status_code, resp.text))
    return resp.json()

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    raw_symbol = data.get("symbol", "").upper()

    if signal == "LIST_POSITIONS":
        list_open_positions()
        return "Listado posiciones enviado", 200

    if not raw_symbol:
        print("❌ No se recibió símbolo")
        return "No symbol", 400

    symbol = raw_symbol
    print(f"✅ Símbolo recibido: {symbol}")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        place_order(symbol, "BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order(symbol, "SELL")
    elif signal and signal.startswith("EXIT"):
        close_positions(symbol)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
