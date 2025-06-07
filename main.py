import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Cargar claves desde entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
SYMBOL = "SOLUSDT"
PRODUCT_TYPE = "USDT-FUTURES"

# 🔎 Verificar si el símbolo es válido en Bitget
def is_symbol_valid(symbol):
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/mix/market/contracts",
            params={"productType": PRODUCT_TYPE}
        )
        contracts = resp.json().get("data", [])
        valid_symbols = [c["symbol"] for c in contracts]
        return symbol in valid_symbols
    except Exception as e:
        print("⚠️ Error verificando símbolo:", str(e))
        return False

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise Exception("❌ Faltan claves de entorno.")

if not is_symbol_valid(SYMBOL):
    raise Exception(f"❌ Símbolo no válido para {PRODUCT_TYPE}: {SYMBOL}")

# 🔏 Firma según Bitget (base64 HMAC-SHA256)
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

# ✅ Crear orden
def place_order(side):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": SYMBOL,
        "marginCoin": "USDT",
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🟢 ORDEN {side} → {resp.status_code}, {resp.text}")

# ❌ Cerrar posiciones
def close_positions():
    print("🔄 Señal de cierre recibida.")
    url = f"/api/v2/mix/position/single-position?symbol={SYMBOL}&marginCoin=USDT"
    headers = auth_headers("GET", f"/api/v2/mix/position/single-position?symbol={SYMBOL}&marginCoin=USDT")
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
            place_close_order("SELL", long_pos)
        if short_pos > 0:
            print("🔴 Cerrando SHORT...")
            place_close_order("BUY", short_pos)
    except Exception as e:
        print("❌ Error al interpretar posición:", str(e))

# 🧨 Orden de cierre
def place_close_order(side, size):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": SYMBOL,
        "marginCoin": "USDT",
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "orderDirection": "close_long" if side == "SELL" else "close_short",
        "productType": PRODUCT_TYPE
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🔴 ORDEN CIERRE {side} → {resp.status_code}, {resp.text}")

# 🌐 Ruta webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        place_order("BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order("SELL")
    elif signal and signal.startswith("EXIT"):
        close_positions()
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

# 🟢 Local debug
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

