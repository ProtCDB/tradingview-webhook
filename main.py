from flask import Flask, request, jsonify
import hmac
import hashlib
import base64
import time
import requests
import json
import uuid
import os

app = Flask(__name__)

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

HEADERS = {
    "Content-Type": "application/json",
    "ACCESS-KEY": API_KEY,
    "ACCESS-PASSPHRASE": API_PASSPHRASE
}

def sign_request(timestamp, method, path, body=""):
    if body:
        body_str = json.dumps(body, separators=(",", ":"))
    else:
        body_str = ""
    pre_hash = f"{timestamp}{method.upper()}{path}{body_str}"
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        pre_hash.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

def get_real_symbol(symbol):
    if symbol.endswith("_UMCBL"):
        return symbol
    return symbol + "_UMCBL"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"📨 Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol", "BTCUSDT")
    real_symbol = get_real_symbol(symbol)

    print(f"✅ Símbolo real encontrado: {real_symbol}")

    if signal == "ENTRY_LONG":
        return place_order(real_symbol, side="open_long")
    elif signal == "ENTRY_SHORT":
        return place_order(real_symbol, side="open_short")
    elif signal == "EXIT_CONFIRMED":
        return close_position(real_symbol)
    else:
        return jsonify({"message": "❓ Señal no reconocida"}), 400

def place_order(symbol, side):
    print(f"🚀 Entrada {'LONG' if side == 'open_long' else 'SHORT'}")

    path = "/api/mix/v1/order/place-order"
    timestamp = str(int(time.time() * 1000))

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": "buy" if side == "open_long" else "sell",
        "orderType": "market",
        "size": "0.1",
        "marginMode": "crossed",
        "positionSide": "long" if side == "open_long" else "short",
        "clientOid": str(uuid.uuid4())
    }

    signature = sign_request(timestamp, "POST", path, body)

    headers = HEADERS.copy()
    headers["ACCESS-TIMESTAMP"] = timestamp
    headers["ACCESS-SIGN"] = signature

    response = requests.post(BASE_URL + path, headers=headers, data=json.dumps(body))
    print(f"🟢 ORDEN {'BUY' if side == 'open_long' else 'SELL'} → {response.status_code}, {response.text}")
    return jsonify({"message": "Order sent", "status": response.status_code, "response": response.json()}), 200

def close_position(symbol):
    print("🔄 Señal de cierre recibida.")

    path = "/api/mix/v1/position/close-position"
    timestamp = str(int(time.time() * 1000))

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "positionSide": "long",  # ajusta si soportas también short
    }

    signature = sign_request(timestamp, "POST", path, body)

    headers = HEADERS.copy()
    headers["ACCESS-TIMESTAMP"] = timestamp
    headers["ACCESS-SIGN"] = signature

    response = requests.post(BASE_URL + path, headers=headers, data=json.dumps(body))
    print(f"📊 Respuesta de posición: {response.json()}")

    if response.status_code != 200:
        print("⚠️ Error al cerrar posición")
    return jsonify({"message": "Exit signal processed", "status": response.status_code, "response": response.json()}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
