import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Claves de API desde variables de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

# 📦 Constantes globales
BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"
MARGIN_MODE = "cross"  # correcto: "cross"
OPEN_TYPE = 1          # unilateral

# 📥 Verifica símbolo y devuelve el nombre real usado por Bitget (ej: "SOLUSDT_UMCBL")
def get_real_symbol(symbol):
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/mix/market/contracts",
            params={"productType": PRODUCT_TYPE}
        )
        contracts = resp.json().get("data", [])
        for c in contracts:
            if c["symbol"].startswith(symbol):
                print(f"✅ Símbolo real encontrado: {c['symbol']}")
                return c["symbol"]
        print("❌ Símbolo no encontrado:", symbol)
    except Exception as e:
        print("❌ Error verificando símbolo:", str(e))
    return None

# 🔏 Genera headers firmados para autenticar con Bitget
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

# 🟢 Orden de entrada (compra o venta)
def place_order(side, symbol_real):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol_real,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE,
        "marginMode": MARGIN_MODE,
        "openType": OPEN_TYPE
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🟢 ORDEN {side} → {resp.status_code}, {resp.text}")

# ❌ Orden de cierre (detecta si hay long o short abierto y cierra)
def close_positions(symbol_real):
    print("🔄 Señal de cierre recibida.")
    url = f"/api/v2/mix/position/single-position?symbol={symbol_real}&marginCoin={MARGIN_COIN}"
    headers = auth_headers("GET", f"/api/v2/mix/position/single-position?symbol={symbol_real}&marginCoin={MARGIN_COIN}")
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
            place_close_order("SELL", long_pos, symbol_real)
        if short_pos > 0:
            print("🔴 Cerrando SHORT...")
            place_close_order("BUY", short_pos, symbol_real)
    except Exception as e:
        print("❌ Error al interpretar posición:", str(e))

# 🧨 Ejecuta orden de cierre
def place_close_order(side, size, symbol_real):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol_real,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "orderDirection": "close_long" if side == "SELL" else "close_short",
        "productType": PRODUCT_TYPE,
        "marginMode": MARGIN_MODE,
        "openType": OPEN_TYPE
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🔴 ORDEN CIERRE {side} → {resp.status_code}, {resp.text}")

# 🌐 Webhook que recibe señales
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    symbol = data.get("symbol")

    if not symbol:
        print("⚠️ Falta símbolo en la señal.")
        return "Missing symbol", 400

    symbol_real = get_real_symbol(symbol)
    if not symbol_real:
        return "Invalid symbol", 400

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        place_order("BUY", symbol_real)
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order("SELL", symbol_real)
    elif signal and signal.startswith("EXIT"):
        close_positions(symbol_real)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

# 🟢 Local test/debug
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
