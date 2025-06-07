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

# === Verificación segura de entorno ===
def verify_env():
    print("🔐 Verificación de entorno:")
    print("  BITGET_API_KEY presente:", bool(API_KEY))
    print("  BITGET_API_SECRET presente:", bool(API_SECRET))
    print("  BITGET_API_PASSPHRASE presente:", bool(PASSPHRASE))

    if not all([API_KEY, API_SECRET, PASSPHRASE]):
        raise Exception("❌ Faltan variables de entorno: BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")

verify_env()

# === Configuración ===
BASE_URL = "https://api.bitget.com"  # Real
SYMBOL = "SOLUSDT"
MARGIN_RATIO = 0.01  # 1% del balance

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

# === Headers de autenticación ===
def auth_headers(method, path, body=""):
    timestamp = get_timestamp()
    prehash = f"{timestamp}{method}{path}{body}"
    signature = sign(prehash)
    headers = HEADERS.copy()
    headers["ACCESS-SIGN"] = signature
    headers["ACCESS-TIMESTAMP"] = timestamp
    return headers

# === Obtener balance USDT ===
def get_balance():
    try:
        url = "/api/v2/mix/account/accounts?productType=USDT"
        full_url = BASE_URL + url
        headers = auth_headers("GET", url)
        resp = requests.get(full_url, headers=headers)
        data = resp.json()
        for asset in data.get("data", []):
            if asset["marginCoin"] == "USDT":
                return float(asset["available"])
    except Exception as e:
        print("❌ Error al obtener balance:", e)
    return 0.0

# === Precio de mercado ===
def get_market_price():
    url = f"/api/v2/mix/market/ticker?symbol={SYMBOL}"
    full_url = BASE_URL + url
    resp = requests.get(full_url)
    return float(resp.json()["data"]["last"])

# === Calcular tamaño de orden ===
def get_order_size(price):
    balance = get_balance()
    if balance <= 0:
        raise Exception("❌ Balance insuficiente.")
    amount = balance * MARGIN_RATIO
    return round(amount / price, 3)

# === Colocar orden ===
def place_order(side):
    try:
        price = get_market_price()
        size = get_order_size(price)
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
        headers = auth_headers("POST", url, json.dumps(body))
        resp = requests.post(full_url, headers=headers, data=json.dumps(body))
        print(f"🟢 ORDEN ENVIADA ({side}): {resp.status_code}, {resp.text}")
    except Exception as e:
        print("❌ Error en place_order:", str(e))

# === Cerrar todas las posiciones ===
def close_positions():
    try:
        # Intentamos cerrar long y short explícitamente
        for direction in ["close_long", "close_short"]:
            url = "/api/v2/mix/order/close-position"
            full_url = BASE_URL + url
            body = {
                "symbol": SYMBOL,
                "marginCoin": "USDT",
                "orderDirection": direction
            }
            headers = auth_headers("POST", url, json.dumps(body))
            resp = requests.post(full_url, headers=headers, data=json.dumps(body))
            print(f"🔴 {direction.upper()} → {resp.status_code}, {resp.text}")
    except Exception as e:
        print("❌ Error en close_positions:", str(e))

# === Endpoint raíz ===
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "✅ Webhook activo", 200

# === Webhook principal ===
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📨 Payload recibido:", data)

        signal = data.get("signal")
        if not signal:
            return jsonify({"error": "No se recibió 'signal'"}), 400

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

# === Iniciar servidor ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

