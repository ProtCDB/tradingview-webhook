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

# ✅ Verificar símbolo válido
def get_valid_symbol(input_symbol):
    try:
        url = f"{BASE_URL}/api/v2/mix/market/contracts"
        resp = requests.get(url, params={"productType": PRODUCT_TYPE})
        contracts = resp.json().get("data", [])
        for c in contracts:
            if c["symbol"].startswith(input_symbol):
                return c["symbol"]
    except Exception as e:
        print("❌ Error obteniendo contratos:", str(e))
    return None

# 🔐 Headers de autenticación
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

# ✅ Crear orden de entrada
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

# ❌ Cerrar posiciones
def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    endpoint = "/api/v2/mix/position/single-position"
    query = f"?symbol={symbol}&marginCoin={MARGIN_COIN}&marginMode=isolated"
    url = endpoint + query
    headers = auth_headers("GET", url)
    resp = requests.get(BASE_URL + url, headers=headers)
    print("📊 Respuesta de posición:", resp.json())

    data = resp.json()
    position = data.get("data")
    if not position:
        print("⚠️ No hay posición abierta para cerrar.")
        return

    try:
        long_pos = float(position.get("long", {}).get("available", 0))
        short_pos = float(position.get("short", {}).get("available", 0))

        if long_pos > 0:
            print("🔴 Cerrando LONG...")
            place_close_order(symbol, "SELL", long_pos)
        if short_pos > 0:
            print("🔴 Cerrando SHORT...")
            place_close_order(symbol, "BUY", short_pos)
    except Exception as e:
        print("❌ Error interpretando posición:", str(e))

# 🧨 Orden de cierre
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

# 🌐 Webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    raw_symbol = data.get("symbol", "").upper()

    real_symbol = get_valid_symbol(raw_symbol)
    if not real_symbol:
        print(f"❌ Símbolo no válido: {raw_symbol}")
        return "Invalid symbol", 400

    print(f"✅ Símbolo real encontrado: {real_symbol}")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        place_order(real_symbol, "BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order(real_symbol, "SELL")
    elif signal and signal.startswith("EXIT"):
        close_positions(real_symbol)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

# 🟢 Local debug
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
