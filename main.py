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

# ✅ Obtener símbolo válido en Bitget (ej: SOLUSDT_UMCBL)
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

# 🔐 Autenticación
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

# 🟢 Listar posiciones abiertas
def list_positions(symbol=None):
    try:
        if symbol == "ALL":
            endpoint = f"/api/v2/mix/position/all-position"
            params = {"productType": PRODUCT_TYPE}
        else:
            real_symbol = get_valid_symbol(symbol)
            if not real_symbol:
                print(f"❌ Símbolo no válido: {symbol}")
                return None
            endpoint = f"/api/v2/mix/position/single-position"
            params = {
                "symbol": real_symbol,
                "marginCoin": MARGIN_COIN
            }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_endpoint = f"{endpoint}?{query_string}"
        headers = auth_headers("GET", full_endpoint)
        url = f"{BASE_URL}{full_endpoint}"
        print(f"📡 Llamando a endpoint: {full_endpoint}")
        resp = requests.get(url, headers=headers)

        if resp.status_code != 200:
            print(f"❌ Error listando posiciones: {resp.status_code} - {resp.text}")
            return None

        return resp.json().get("data", None)

    except Exception as e:
        print("❌ Excepción al listar posiciones:", str(e))
        return None

# 🟢 Crear orden de entrada
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

# 🔴 Orden de cierre
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

# 🔄 Cerrar posiciones
def close_positions(symbol):
    endpoint = f"/api/v2/mix/position/single-position"
    real_symbol = get_valid_symbol(symbol)
    if not real_symbol:
        print(f"❌ Símbolo no válido: {symbol}")
        return

    params = f"?symbol={real_symbol}&marginCoin={MARGIN_COIN}"
    full_endpoint = endpoint + params
    headers = auth_headers("GET", full_endpoint)
    resp = requests.get(BASE_URL + full_endpoint, headers=headers)

    if resp.status_code != 200:
        print(f"❌ Error al obtener posición: {resp.status_code} - {resp.text}")
        return

    data = resp.json().get("data")
    if not data:
        print("⚠️ No hay posición abierta.")
        return

    try:
        long_pos = float(data.get("long", {}).get("available", 0))
        short_pos = float(data.get("short", {}).get("available", 0))
        if long_pos > 0:
            place_close_order(real_symbol, "SELL", long_pos)
        if short_pos > 0:
            place_close_order(real_symbol, "BUY", short_pos)
    except Exception as e:
        print("❌ Error procesando posición:", str(e))

# 🌐 Webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    raw_symbol = data.get("symbol", "").upper()

    if signal == "LIST_POSITIONS":
        result = list_positions(raw_symbol)
        print("📋 Posiciones abiertas:", json.dumps(result, indent=2))
        return "OK", 200

    real_symbol = get_valid_symbol(raw_symbol)
    if not real_symbol:
        print(f"❌ Símbolo no válido: {raw_symbol}")
        return "Invalid symbol", 400

    print(f"✅ Símbolo real encontrado: {real_symbol}")

    if signal == "ENTRY_LONG":
        place_order(real_symbol, "BUY")
    elif signal == "ENTRY_SHORT":
        place_order(real_symbol, "SELL")
    elif signal and signal.startswith("EXIT"):
        close_positions(real_symbol)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

# 🟢 Debug local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
