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
PRODUCT_TYPE = "USDT-FUTURES"

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise Exception("❌ Faltan claves de entorno.")

# 🔎 Obtener el símbolo real basado en el símbolo simple (ej: SOLUSDT → SOLUSDT_UMCBL)
def get_real_symbol(simple_symbol):
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/mix/market/contracts",
            params={"productType": PRODUCT_TYPE}
        )
        contracts = resp.json().get("data", [])
        for contract in contracts:
            if contract["symbol"].startswith(simple_symbol):
                print(f"✅ Símbolo real encontrado: {contract['symbol']}")
                return contract["symbol"]
        return None
    except Exception as e:
        print("⚠️ Error buscando símbolo real:", str(e))
        return None

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

def place_order(symbol, side):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol,
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
    print(f"🟢 ORDEN {side} para {symbol} → {resp.status_code}, {resp.text}")

# ❌ Cerrar posiciones
def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    url = f"/api/v2/mix/position/single-position?symbol={symbol}&marginCoin=USDT"
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
        print("❌ Error al interpretar posición:", str(e))

# 🧨 Orden de cierre
def place_close_order(symbol, side, size):
    url = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol,
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
    print(f"🔴 ORDEN CIERRE {side} para {symbol} → {resp.status_code}, {resp.text}")

# 🌐 Ruta webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    simple_symbol = data.get("symbol", "SOLUSDT")
    real_symbol = get_real_symbol(simple_symbol)

    if not real_symbol:
        print(f"❌ No se encontró símbolo real para {simple_symbol}")
        return "Error: símbolo no válido", 400

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

