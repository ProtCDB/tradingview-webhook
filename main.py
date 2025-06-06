import os
import hmac
import time
import hashlib
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_URL = "https://api-demo.bitget.com"  # Cambia a https://api.bitget.com si vas a real
SYMBOL = "SOLUSDT"
MARGIN_RATIO = 0.01  # Usa el 1% del balance disponible

# === Obtener credenciales desde variables de entorno ===
def get_api_credentials():
    API_KEY = os.getenv("BITGET_API_KEY")
    API_SECRET = os.getenv("BITGET_API_SECRET")
    PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

    if not API_KEY or not API_SECRET or not PASSPHRASE:
        raise Exception("❌ Faltan variables de entorno: BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

    return API_KEY, API_SECRET, PASSPHRASE

# === Timestamp ===
def get_timestamp():
    return str(int(time.time() * 1000))

# === Firma HMAC ===
def sign(message: str, secret: str):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

# === Autenticación ===
def auth_headers(method, path, body=""):
    API_KEY, API_SECRET, PASSPHRASE = get_api_credentials()
    timestamp = get_timestamp()
    prehash = f"{timestamp}{method}{path}{body}"
    signature = sign(prehash, API_SECRET)

    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

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

# === Obtener precio de mercado ===
def get_market_price():
    url = f"/api/v2/mix/market/ticker?symbol={SYMBOL}"
    full_url = BASE_URL + url
    resp = requests.get(full_url)
    print("💰 Precio de mercado:", resp.json())
    return float(resp.json()["data"]["last"])

# === Calcular tamaño de orden ===
def get_order_size(price):
    balance = get_balance()
    amount = balance * MARGIN_RATIO
    return round(amount / price, 3)

# === Ejecutar orden ===
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

# === Cerrar posiciones ===
def close_positions():
    try:
        url = "/api/v2/mix/position/close-position"
        full_url = BASE_URL + url
        body = {
            "symbol": SYMBOL,
            "marginCoin": "USDT"
        }
        json_body = json.dumps(body)
        headers = auth_headers("POST", url, json_body)
        resp = requests.post(full_url, headers=headers, data=json_body)
        print(f"🔴 CIERRE FORZADO: {resp.status_code}, {resp.text}")
    except Exception as e:
        print("❌ Error en close_positions:", str(e))

# === Endpoint keep-alive ===
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "✅ Webhook activo", 200

# === Webhook principal ===
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📨 Payload recibido:", data)

        if not data or "signal" not in data:
            return jsonify({"error": "No se recibió 'signal' en el JSON"}), 400

        signal = data["signal"]

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
