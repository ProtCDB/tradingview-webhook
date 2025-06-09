import os
import time
import hmac
import hashlib
import base64
import json
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

BASE_URL = "https://api.bitget.com"
MARGIN_COIN = "USDT"

app = Flask(__name__)

def get_timestamp():
    return str(int(time.time() * 1000))

def sign(message, secret):
    secret_bytes = secret.encode()
    message_bytes = message.encode()
    return base64.b64encode(hmac.new(secret_bytes, message_bytes, hashlib.sha256).digest()).decode()

def auth_headers(method, endpoint, body=""):
    timestamp = get_timestamp()
    prehash = timestamp + method.upper() + endpoint + body
    signature = sign(prehash, API_SECRET)

    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    params = {"symbol": symbol, "marginCoin": MARGIN_COIN}
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    endpoint_base = "/api/v2/mix/position/single-position"
    endpoint_full = f"{endpoint_base}?{qs}"

    headers = auth_headers("GET", endpoint_full)
    print("📤 GET:", endpoint_full)
    print("📥 Headers:", headers)

    resp = requests.get(BASE_URL + endpoint_full, headers=headers)
    print("📊 Respuesta de posición:", resp.status_code, resp.text)

    data = resp.json()
    if not data.get("data"):
        print("⚠️ No hay posición abierta para cerrar.")
        return

    # Aquí iría la lógica para cerrar la posición si existe una activa
    # Por ahora solo mostramos los datos
    print("📈 Posición abierta detectada:", data["data"])

@app.route("/", methods=["POST"])
def webhook():
    payload = request.json
    print("📨 Payload recibido:", payload)

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if not signal or not symbol:
        return "Missing data", 400

    print("✅ Símbolo real encontrado:", symbol)

    if signal == "EXIT_CONFIRMED":
        close_positions(symbol)

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
