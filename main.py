import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# Claves desde variables de entorno (nunca las pongas directo en código)
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

# Constantes para Futuros USDT
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

# ✅ Obtener el símbolo real desde Bitget
def get_valid_symbol(input_symbol):
    try:
        url = f"{BASE_URL}/api/v2/mix/market/contracts"
        resp = requests.get(url, params={"productType": PRODUCT_TYPE})
        contracts = resp.json().get("data", [])
        for c in contracts:
            if c["symbol"].startswith(input_symbol):
                return c["symbol"]  # Ejemplo: SOLUSDT_UMCBL
    except Exception as e:
        print("❌ Error obteniendo contratos:", str(e))
    return None

# 🔐 Headers autenticados
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
    endpoint = f"/api/mix/v1/position/singlePosition"
    params = f"?symbol={symbol}&marginCoin={MARGIN_COIN}"
    full_endpoint = endpoint + params
    headers = auth_headers("GET", full_endpoint)
    print(f"📡 Llamando a endpoint: {full_endpoint}")
    resp = requests.get(BASE_URL + full_endpoint, headers=headers)

    if resp.status_code != 200:
        print(f"❌ Error al obtener posición: Status {resp.status_code} - {resp.text}")
        return

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
        "reduceOnly
