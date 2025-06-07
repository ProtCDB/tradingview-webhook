import os
import json
import hmac
import hashlib
import time
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Variables de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
SYMBOL = "SOLUSDT"
MARGIN_COIN = "USDT"

if not all([API_KEY, API_SECRET, API_PASSPHRASE]):
    raise Exception("❌ Faltan variables de entorno BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

# 🔏 Firma
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

# ✅ Entrada
def place_order(side):
    endpoint = "/api/v2/mix/order/place-order"
    full_url = BASE_URL + endpoint
    body = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": "USDT-FUTURES"
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", endpoint, json_body)
    requests.post(full_url, headers=headers, data=json_body)

# ❌ Cierre
def close_positions():
    try:
        endpoint = f"/api/v2/mix/position/single-position?symbol={SYMBOL}&marginCoin={MARGIN_COIN}"
        full_url = BASE_URL + endpoint
        headers = auth_headers("GET", f"/api/v2/mix/position/single-position", f"symbol={SYMBOL}&marginCoin={MARGIN_COIN}")
        resp = requests.get(full_url, headers=headers)
        data = resp.json()

        position = data.get("data")
        if not position:
            return

        long_pos = float(position.get("long", {}).get("available", 0))
        short_pos = float(position.get("short", {}).get("available", 0))

        if long_pos > 0:
            place_close_order("SELL", long_pos)

        if short_pos > 0:
            place_close_order("BUY", short_pos)

    except Exception:
        pass

def place_close_order(side, size):
    endpoint = "/api/v2/mix/order/place-order"
    full_url = BASE_URL + endpoint
    body = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "orderDirection": "close_long" if side == "SELL" else "close_short",
        "productType": "USDT-FUTURES"
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", endpoint, json_body)
    requests.post(full_url, headers=headers, data=json_body)

# 🌐 Webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    signal = data.get("signal") or data.get("action")

    if signal == "ENTRY_LONG" or signal == "BUY":
        place_order("BUY")
    elif signal == "ENTRY_SHORT" or signal == "SELL":
        place_order("SELL")
    elif signal in ["EXIT_LONG_TP", "EXIT_LONG_SL", "EXIT_SHORT_TP", "EXIT_SHORT_SL", "EXIT_CONFIRMED"]:
        close_positions()

    return "OK", 200
