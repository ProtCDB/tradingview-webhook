import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# Claves de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

if not all([API_KEY, API_SECRET, API_PASSPHRASE]):
    raise Exception("❌ Faltan claves de entorno.")

# Firmar la petición
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

# Verifica si el símbolo existe
def is_symbol_valid(symbol):
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/mix/market/contracts",
            params={"productType": PRODUCT_TYPE}
        )
        data = resp.json().get("data", [])
        valid_symbols = [item["symbol"] for item in data]
        return symbol in valid_symbols
    except Exception as e:
        print("⚠️ Error verificando símbolo:", e)
        return False

# Coloca orden de entrada
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
        "marginMode": "crossed",
        "presetTakeProfitPrice": "",
        "presetStopLossPrice": ""
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🟢 ORDEN {side} → {resp.status_code}, {resp.text}")

# Coloca orden de cierre
def place_close_order(symbol, side, size):
    url = "/api/v2/mix/order/place-order"
    direction = "close_long" if side == "SELL" else "close_short"
    body = {
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "orderDirection": direction,
        "productType": PRODUCT_TYPE,
        "marginMode": "crossed"
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(BASE_URL + url, headers=headers, data=json_body)
    print(f"🔴 ORDEN CIERRE {side} → {resp.status_code}, {resp.text}")

# Cierra posición si existe
def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    url = f"/api/v2/mix/position/single-position?symbol={symbol}&marginCoin={MARGIN_COIN}"
    headers = auth_headers("GET", url)
    resp = requests.get(BASE_URL + url, headers=headers)
    print("📊 Respuesta de posición:", resp.json())

    data = resp.json().get("data", {})
    long_pos = float(data.get("long", {}).get("available", 0))
    short_pos = float(data.get("short", {}).get("available", 0))

    if long_pos > 0:
        print("🔴 Cerrando LONG...")
        place_close_order(symbol, "SELL", long_pos)
    elif short_pos > 0:
        print("🔴 Cerrando SHORT...")
        place_close_order(symbol, "BUY", short_pos)
    else:
        print("⚠️ No hay posición abierta para cerrar.")

# Webhook endpoint
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)

    signal = data.get("signal")
    symbol = data.get("symbol")

    if not symbol or not is_symbol_valid(symbol):
        print(f"❌ Símbolo no válido: {symbol}")
        return "Invalid symbol", 400

    print(f"✅ Símbolo real encontrado: {symbol}")

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

# Ejecución local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
