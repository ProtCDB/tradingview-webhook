import json
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "TU_API_KEY"
API_SECRET = "TU_API_SECRET"
API_PASS = "TU_API_PASSPHRASE"
BASE_URL = "https://api.bitget.com"
MARGIN_COIN = "USDT"

# ---------------------- FIRMA ----------------------
def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(method, endpoint, timestamp, body=""):
    prehash = timestamp + method.upper() + endpoint + body
    return hmac.new(
        API_SECRET.encode(),
        prehash.encode(),
        hashlib.sha256
    ).hexdigest()

# ---------------------- FUNCIONES API ----------------------
def send_order(symbol, side):
    endpoint = "/api/mix/v1/order/place-order"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "0.1",
        "tradeSide": "open"
    }

    timestamp = get_timestamp()
    signature = sign_request("POST", endpoint, timestamp, json.dumps(body))

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASS,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    print(f"🟢 ORDEN {side.upper()} → {response.status_code}, {response.text}")
    return response

def close_position(symbol):
    endpoint = "/api/mix/v1/position/singlePosition"
    query = f"symbol={symbol}&marginCoin={MARGIN_COIN}"
    url = BASE_URL + endpoint + "?" + query

    timestamp = get_timestamp()
    signature = sign_request("GET", endpoint + "?" + query, timestamp)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASS,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(f"📡 Llamando a endpoint: {endpoint}?{query}")

    if response.status_code != 200:
        print(f"❌ Error al obtener posición: Status {response.status_code} - {response.text}")
        return

    try:
        data = response.json().get("data")
        if not data or float(data.get("total", 0)) == 0:
            print("⚠️ No hay posición abierta para cerrar.")
            return

        side = "close_long" if data["holdSide"] == "long" else "close_short"

        order_body = {
            "symbol": symbol,
            "marginCoin": MARGIN_COIN,
            "side": "sell" if side == "close_long" else "buy",
            "orderType": "market",
            "size": data["total"],
            "tradeSide": side
        }

        close_endpoint = "/api/mix/v1/order/place-order"
        url = BASE_URL + close_endpoint

        timestamp = get_timestamp()
        signature = sign_request("POST", close_endpoint, timestamp, json.dumps(order_body))

        headers["ACCESS-SIGN"] = signature
        headers["ACCESS-TIMESTAMP"] = timestamp

        close_response = requests.post(url, headers=headers, data=json.dumps(order_body))
        print(f"🔁 Orden de cierre enviada: {close_response.status_code}, {close_response.text}")

    except Exception as e:
        print(f"❌ Error interpretando posición: {e}")

# ---------------------- FLASK WEBHOOK ----------------------
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"\ud83d\udce8 Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol")

    if not symbol:
        return jsonify({"error": "Símbolo no proporcionado"}), 400

    print(f"✅ Símbolo recibido: {symbol}")

    if signal == "ENTRY_LONG":
        print("\ud83d\ude80 Entrada LONG")
        return jsonify(send_order(symbol, "buy").json())

    elif signal == "ENTRY_SHORT":
        print("\ud83d\udcc9 Entrada SHORT")
        return jsonify(send_order(symbol, "sell").json())

    elif signal == "EXIT_CONFIRMED":
        print("\ud83d\udd04 Se\u00f1al de cierre recibida.")
        close_position(symbol)
        return jsonify({"status": "Cierre intentado"})

    elif signal == "LIST_POSITIONS":
        print("\ud83d\udccb Listar posiciones abiertas no implementado.")
        return jsonify({"status": "No implementado"})

    return jsonify({"error": "Se\u00f1al no v\u00e1lida"}), 400

# ---------------------- RUN ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
