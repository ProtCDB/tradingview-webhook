import os
import json
import hmac
import hashlib
import time
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Configuración
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
SYMBOL = "SOLUSDT"
MARGIN_COIN = "USDT"
PRODUCT_TYPE = "USDT-FUTURES"

# ✅ Verificación de entorno
print("🔐 Verificación de entorno:")
print("  BITGET_API_KEY presente:", bool(API_KEY))
print("  BITGET_API_SECRET presente:", bool(API_SECRET))
print("  BITGET_API_PASSPHRASE presente:", bool(API_PASSPHRASE))

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise Exception("❌ Faltan variables de entorno: BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

# 🔏 Firma HMAC para autenticación
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

# ✅ Orden de entrada
def place_order(side):
    url = "/api/v2/mix/order/place-order"
    full_url = BASE_URL + url
    body = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "1",  # Ajusta el tamaño según tus necesidades
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE
    }
    json_body = json.dumps(body)
    headers = auth_headers("POST", url, json_body)
    resp = requests.post(full_url, headers=headers, data=json_body)
    print(f"📥 Entrada {side} → {resp.status_code}, {resp.text}")

# ❌ Cierre de posición
def close_positions():
    try:
        endpoint_path = "/api/v2/mix/position/single-position"
        query = f"symbol={SYMBOL}&marginCoin={MARGIN_COIN}"
        full_url = f"{BASE_URL}{endpoint_path}?{query}"

        # ⚠️ Para firmar correctamente un GET, NO se incluye la query en el body
        headers = auth_headers("GET", endpoint_path)

        resp = requests.get(full_url, headers=headers)
        data = resp.json()
        print("📊 Respuesta de posición:", data)

        position = data.get("data")
        if not position:
            print("⚠️ No hay posición abierta para cerrar.")
            return

        long_pos = float(position.get("long", {}).get("available", 0))
        short_pos = float(position.get("short", {}).get("available", 0))

        if long_pos > 0:
            print(f"🔴 Cerrando posición LONG ({long_pos})...")
            place_close_order("SELL", long_pos)

        if short_pos > 0:
            print(f"🔴 Cerrando posición SHORT ({short_pos})...")
            place_close_order("BUY", short_pos)

    except Exception as e:
        print("❌ Error en close_positions:", str(e))

# 🛑 Colocar orden de cierre
def place_close_order(side, size):
    try:
        url = "/api/v2/mix/order/place-order"
        full_url = BASE_URL + url
        body = {
            "symbol": SYMBOL,
            "marginCoin": MARGIN_COIN,
            "side": side,
            "orderType": "market",
            "size": str(size),
            "timeInForceValue": "normal",
            "orderDirection": "close_long" if side == "SELL" else "close_short",
            "productType": PRODUCT_TYPE
        }
        json_body = json.dumps(body)
        headers = auth_headers("POST", url, json_body)
        resp = requests.post(full_url, headers=headers, data=json_body)
        print(f"🔴 CLOSE {side} → {resp.status_code}, {resp.text}")
    except Exception as e:
        print("❌ Error en place_close_order:", str(e))

# 🌐 Webhook principal
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    print("📨 Payload recibido:", data)

    signal = data.get("signal")

    if signal == "ENTRY_LONG":
        print("📈 Señal de entrada LONG")
        place_order("BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Señal de entrada SHORT")
        place_order("SELL")
    elif signal in ["EXIT_LONG_TP", "EXIT_LONG_SL", "EXIT_SHORT_TP", "EXIT_SHORT_SL", "EXIT_CONFIRMED"]:
        print(f"📤 Señal de salida recibida: {signal}")
        close_positions()
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

# 🟢 Modo local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
