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

# Obtener lista de símbolos válidos
def get_valid_symbol(input_symbol):
    try:
        url = f"{BASE_URL}/api/v2/mix/market/contracts"
        resp = requests.get(url, params={"productType": PRODUCT_TYPE})
        contracts = resp.json().get("data", [])
        for c in contracts:
            # Retorna el símbolo corto (sin sufijo)
            if c["symbol"].startswith(input_symbol):
                return c["symbol"]
    except Exception as e:
        print("❌ Error obteniendo contratos:", str(e))
    return None

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

def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    full_endpoint = f"/api/mix/v1/position/singlePosition?symbol={symbol}&marginCoin={MARGIN_COIN}"
    headers = auth_headers("GET", full_endpoint)
    resp = requests.get(BASE_URL + full_endpoint, headers=headers)
    print(f"📡 Llamando a endpoint: {full_endpoint}")
    
    if resp.status_code != 200:
        print(f"❌ Error al obtener posición: Status {resp.status_code} - {resp.text}")
        return

    data = resp.json()
    # Aquí comprobamos si la data es lista o diccionario
    position_data = data.get("data")
    if isinstance(position_data, list):
        print("⚠️ La posición recibida es lista, procesando primer elemento")
        if len(position_data) == 0:
            print("⚠️ Lista vacía, no hay posiciones abiertas.")
            return
        position = position_data[0]  # Tomamos el primer objeto
    elif isinstance(position_data, dict):
        position = position_data
    else:
        print(f"❌ Formato inesperado de posición: {position_data}")
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

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    raw_symbol = data.get("symbol", "").upper()
    
    # Obtenemos el símbolo válido para órdenes (símbolo corto)
    valid_symbol = get_valid_symbol(raw_symbol)
    
    if not valid_symbol:
        print(f"❌ Símbolo no válido: {raw_symbol}")
        return "Invalid symbol", 400
    
    print(f"✅ Símbolo recibido: {raw_symbol}")
    print(f"✅ Símbolo para órdenes: {valid_symbol}")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        # Usar símbolo corto para ordenar
        place_order(valid_symbol, "BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order(valid_symbol, "SELL")
    elif signal and signal.startswith("EXIT"):
        # Para cierre usar el símbolo tal cual viene (símbolo completo)
        close_positions(raw_symbol)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
