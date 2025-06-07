import os
import json
import hmac
import hashlib
import time
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Cargar claves desde entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
SYMBOL = "SOLUSDT"  # Usa SOL-USDT si Bitget lo requiere

# 🚨 Verificación al iniciar
print("🔐 Verificación de entorno:")
print("  BITGET_API_KEY presente:", bool(API_KEY))
print("  BITGET_API_SECRET presente:", bool(API_SECRET))
print("  BITGET_API_PASSPHRASE presente:", bool(API_PASSPHRASE))

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise Exception("❌ Faltan variables de entorno: BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

# 🔏 Firma con base64

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

# ✅ Colocar orden de entrada

def place_order(side):
    url = "/api/v2/mix/order/place-order"
    full_url = BASE_URL + url
    body = {
        "symbol": SYMBOL,
        "marginCoin": "USDT",
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": "USDT-FUTURES"
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(full_url, headers=headers, data=json_body)
    print(f"\ud83d\udcc5 {side} → {resp.status_code}, {resp.text}")

# ❌ Cierre inteligente

def close_positions():
    try:
        path = "/api/v2/mix/position/single-position"
        query = f"symbol={SYMBOL}&marginCoin=USDT"
        full_url = BASE_URL + path + "?" + query
        headers = auth_headers("GET", path + "?" + query)

        resp = requests.get(full_url, headers=headers)
        data = resp.json()
        print(f"\ud83d\udcca Posici\u00f3n actual:", data)

        position = data.get("data")
        if not position:
            print("\u274c No se pudo obtener la posici\u00f3n actual.")
            return

        long_pos = float(position.get("long", {}).get("available", 0))
        short_pos = float(position.get("short", {}).get("available", 0))

        if long_pos > 0:
            print("\ud83d\udd34 Cerrando posici\u00f3n LONG...")
            place_close_order("SELL", long_pos)

        if short_pos > 0:
            print("\ud83d\udd34 Cerrando posici\u00f3n SHORT...")
            place_close_order("BUY", short_pos)

    except Exception as e:
        print("\u274c Error en close_positions:", str(e))


def place_close_order(side, size):
    try:
        url = "/api/v2/mix/order/place-order"
        full_url = BASE_URL + url
        body = {
            "symbol": SYMBOL,
            "marginCoin": "USDT",
            "side": side,
            "orderType": "market",
            "size": str(size),
            "timeInForceValue": "normal",
            "orderDirection": "close_long" if side == "SELL" else "close_short",
            "productType": "USDT-FUTURES"
        }
        json_body = json.dumps(body)
        headers = auth_headers("POST", url, json_body)
        resp = requests.post(full_url, headers=headers, data=json_body)
        print(f"\ud83d\udd34 CLOSE_{side} → {resp.status_code}, {resp.text}")
    except Exception as e:
        print("\u274c Error en place_close_order:", str(e))


# 🌐 Webhook principal
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("\ud83d\udce8 Payload recibido:", data)

    signal = data.get("signal") or data.get("action")  # Admite formato TradingView o propio

    if signal == "ENTRY_LONG" or signal == "buy":
        place_order("BUY")
    elif signal == "ENTRY_SHORT" or signal == "sell":
        place_order("SELL")
    elif signal in ["EXIT_CONFIRMED", "close"]:
        close_positions()
    else:
        print("\u26a0\ufe0f Se\u00f1al desconocida:", signal)

    return "OK", 200

# 🟢 Ejecutar localmente (no usado en Render)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
