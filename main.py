from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os

app = Flask(__name__)

# Credenciales desde variables de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_SECRET")
PASSPHRASE = os.getenv("BITGET_PASSPHRASE")

# Configuración del mercado
SYMBOL = "SOLUSDT"
MARGIN_COIN = "USDT"

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(timestamp, method, request_path, body=""):
    prehash = f"{timestamp}{method.upper()}{request_path}{body}"
    signature = hmac.new(
        bytes(API_SECRET, encoding="utf-8"),
        prehash.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    return signature

def close_positions():
    timestamp = get_timestamp()
    method = "POST"
    path = "/api/v2/mix/order/close-position"
    url = f"https://api.bitget.com{path}"

    body = {
        "symbol": SYMBOL,
        "marginCoin": MARGIN_COIN
    }
    import json
    body_json = json.dumps(body)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign_request(timestamp, method, path, body_json),
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=body_json)
    return response.json()

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"📩 Alerta recibida: {data}")

    signal = data.get("signal")

    if signal == "EXIT_CONFIRMED":
        print("🚨 Señal EXIT_CONFIRMED recibida. Cerrando posiciones...")
        result = close_positions()
        print(f"📤 Respuesta de Bitget: {result}")
        return jsonify({"status": "Posición cerrada", "bitget_response": result}), 200

    return jsonify({"status": "Alerta recibida", "detalles": signal}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
