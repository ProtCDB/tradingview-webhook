import os
import hmac
import time
import hashlib
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# === Variables de entorno ===
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

# === DEBUG de entorno ===
print("🔐 Verificación de entorno:")
print("  BITGET_API_KEY presente:", bool(API_KEY))
print("  BITGET_API_SECRET presente:", bool(API_SECRET))
print("  BITGET_API_PASSPHRASE presente:", bool(PASSPHRASE))

# Validación
if not API_KEY or not API_SECRET or not PASSPHRASE:
    raise Exception("❌ Faltan variables de entorno: BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

# === Configuración ===
BASE_URL = "https://api.bitget.com"  # URL REAL para entorno de producción
SYMBOL = "SOLUSDT"
MARGIN_RATIO = 0.01  # 1% del balance disponible

HEADERS = {
    "ACCESS-KEY": API_KEY,
    "ACCESS-PASSPHRASE": PASSPHRASE,
    "Content-Type": "application/json"
}

# === Timestamp ===
def get_timestamp():
    return str(int(time.time() * 1000))

# === Firma HMAC ===
def sign(message: str):
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

# === Headers con firma ===
def auth_headers(method, path, body=""):
    timestamp = get_timestamp()
    prehash = f"{timestamp}{method}{path}{body}"
    signature = sign(prehash)
    headers = HEADERS.copy()
    headers["ACCESS-SIGN"] = signature
    headers["ACCESS-TIMESTAMP"] = timestamp
    return headers

# === Obtener balance USDT disponible ===
def get_balance():
    url = "/api/v2/mix/account/accounts?productType=USDT"
    full_url = BASE_URL + url
    headers = auth_headers("GET", url)
    resp = requests.get(full_url, headers=headers)
    data = resp.json()
    print("📊 Balance response:", data)
    for asset in data.get("data", []):
        if asset["marginCoin"] == "USDT":
            return float(asset["available"])
    return 0.0

# === Precio de mercado ===
def get_market_price():
    url = f"/api/v2/mix/market/ticker?symbol={SYMBOL}"
    full_url = BASE_URL + url
    resp = requests.get(full_url)
    return float(resp.json()["data"]["last"])

# === Tamaño de orden ===
def get_order_size(price):
    balance = get_balance()
    amount = balance * MARGIN_RATIO
    return round(amount / price, 3)

# === Crear orden ===
def place_order(side):
    try:
        market_price = get_market_price()
        size = get_order_size(market_price)
        direction = "open_long" if side == "BUY" else "open_short"

        url = "/api/v2/mix/order/place-order"
        full_url = BASE_URL + url
        body = {
            "symbol": SYMBOL,
            "marginCoin": "USDT",
            "side": side,
            "orderType": "market",
            "size": str(size),
            "price": "",
            "timeInForceValue": "normal",
            "orderDirection": direction,
            "productType": "USDT-FUTURES"
        }
        json_body = json.dumps(body)
        headers = auth_headers("POST", url, json_body)
        resp = requests.post(full_url, headers=headers, data=json_body)
        print(f"🟢 ORDEN ENVIADA ({side}): {resp.status_code}, {resp.text}")
    except Exception as e:
        print("❌ Error en place_order:", str(e))

# === Cerrar posiciones correctamente ===
def close_positions():
    try:
        # Obtener datos de posición actual
        url = f"/api/v2/mix/position/single-position?symbol={SYMBOL}&marginCoin=USDT"
        full_url = BASE_URL + url
        headers = auth_headers("GET", url)
        resp = requests.get(full_url, headers=headers)
        position_data = resp.json()
        print("📦 Posición actual:", position_data)

        if not position_data.get("data"):
            print("⚠️ No hay posición abierta.")
            return

        pos = position_data["data"]
        side = pos["holdSide"]  # "long" o "short"
        size = float(pos["total"])

        if size == 0:
            print("✅ No hay posición abierta.")
            return

        close_side = "SELL" if side == "long" else "BUY"
        direction = "close_long" if side == "long" else "close_short"

        url = "/api/v2/mix/order/place-order"
        full_url = BASE_URL + url
        body = {
            "symbol": SYMBOL,
            "marginCoin": "USDT",
            "side": close_side,
            "orderType": "market",
            "size": str(size),
            "price": "",
            "timeInForceValue": "normal",
            "orderDirection": direction,
            "productType": "USDT-FUTURES"
        }
        json_body = json.dumps(body)
        headers = auth_headers("POST", url, json_body)
        resp = requests.post(full_url, headers=headers, data=json_body)
        print(f"🔴 ORDEN DE CIERRE ENVIADA: {resp.status_code}, {resp.text}")

    except Exception as e:
        print("❌ Error en close_positions:", str(e))

# === Keep-alive ===
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "✅ Webhook activo", 200

# === Webhook ===
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📨 Payload recibido:", data)

        signal = data.get("signal")

        if signal == "ENTRY_LONG":
            place_order("BUY")
        elif signal == "ENTRY_SHORT":
            place_order("SELL")
        elif signal in ["EXIT_CONFIRMED", "EXIT_LONG_SL", "EXIT_LONG_TP", "EXIT_SHORT_SL", "EXIT_SHORT_TP"]:
            close_positions()
        else:
            print("⚠️ Señal no reconocida:", signal)

        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"⚠️ Error general en webhook: {e}")
        return jsonify({"error": str(e)}), 400

# === Ejecutar localmente ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
