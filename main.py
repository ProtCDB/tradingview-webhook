import os
import hmac
import time
import hashlib
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# === Configuración ===
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitgetapi.com"
SYMBOL = "SOLUSDT"
MARGIN_RATIO = 0.01  # Usa el 1% del balance disponible para la orden

HEADERS = {
    "ACCESS-KEY": API_KEY,
    "ACCESS-PASSPHRASE": PASSPHRASE,
    "Content-Type": "application/json"
}

def get_timestamp():
    return str(int(time.time() * 1000))

def sign(message: str):
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def auth_headers(method, path, body=""):
    timestamp = get_timestamp()
    prehash = f"{timestamp}{method}{path}{body}"
    signature = sign(prehash)
    headers = HEADERS.copy()
    headers["ACCESS-SIGN"] = signature
    headers["ACCESS-TIMESTAMP"] = timestamp
    return headers

# === Obtener balance disponible en USDT ===
def get_balance():
    url = "/api/v2/mix/account/accounts?productType=USDT"
    full_url = BASE_URL + url
    headers = auth_headers("GET", url)
    resp = requests.get(full_url, headers=headers)
    data = request.get_json(force=True)
    for asset in data["data"]:
        if asset["marginCoin"] == "USDT":
            return float(asset["available"])
    return 0.0

# === Calcular tamaño de orden ===
def get_order_size(price):
    balance = get_balance()
    amount = balance * MARGIN_RATIO
    return round(amount / price, 3)

# === Obtener precio actual del mercado ===
def get_market_price():
    url = f"/api/v2/mix/market/ticker?symbol={SYMBOL}"
    full_url = BASE_URL + url
    resp = requests.get(full_url)
    return float(resp.json()["data"]["last"])

# === Ejecutar orden ===
def place_order(side):
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

# === Cerrar todas las posiciones ===
def close_positions():
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

# === Ruta opcional para responder a GET y HEAD (Render keep-alive) ===
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "👋 Webhook activo", 200

# === Webhook Handler ===
@app.route("/", methods=["POST"])
def webhook():
    try:
        print("=== Nueva solicitud recibida ===")
        print("🔍 Headers:")
        print(dict(request.headers))
        print("📦 request.data:")
        print(request.data)
        print("📤 request.get_data(as_text=True):")
        print(request.get_data(as_text=True))

        json_data = request.get_json(force=True)
        print("✅ JSON parseado:", json_data)

        signal = json_data.get("signal", "")
        print(f"📍 Señal recibida: {signal}")

        if signal == "ENTRY_LONG":
            place_order("BUY")
        elif signal == "ENTRY_SHORT":
            place_order("SELL")
        elif signal in ["EXIT_CONFIRMED", "EXIT_LONG_SL", "EXIT_LONG_TP", "EXIT_SHORT_SL", "EXIT_SHORT_TP"]:
            close_positions()
        else:
            print("❌ Señal no reconocida")

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"⚠️ Error procesando webhook: {e}")
        return jsonify({"error": str(e)}), 400




# === Iniciar Servidor ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
