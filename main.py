import os
import json
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time

app = Flask(__name__)

# Leer las claves de entorno (evita hardcodear en github)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

BASE_URL = "https://contract.mexc.com"

def sign(params: dict, secret: str):
    qs = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()

def call_api(method, path, params=None):
    if params is None:
        params = {}
    timestamp = int(time.time() * 1000)
    params['api_key'] = API_KEY
    params['req_time'] = timestamp
    params['sign'] = sign(params, API_SECRET)

    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}

    if method == 'GET':
        response = requests.get(url, params=params, headers=headers)
    else:  # POST
        response = requests.post(url, json=params, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Status {response.status_code} - {response.text}")

    return response.json()

def get_real_symbol(symbol):
    # Aquí podemos ajustar si hace falta alguna conversión,
    # o devolver directamente el símbolo sin modificar.
    # Por ahora devolvemos tal cual:
    return symbol

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.json
        signal = data.get("signal")
        symbol = data.get("symbol")

        if not API_KEY or not API_SECRET:
            return jsonify({"error": "API_KEY o API_SECRET no configurados en variables de entorno"}), 500

        if not signal or not symbol:
            return jsonify({"error": "Faltan parámetros 'signal' o 'symbol'"}), 400

        real_symbol = get_real_symbol(symbol)
        print(f"📨 Payload recibido: {data}")
        print(f"✅ Símbolo real encontrado: {real_symbol}")

        if signal == "LIST_POSITIONS":
            # Llamamos al endpoint para obtener posiciones abiertas
            try:
                # La documentación sugiere este endpoint para posiciones abiertas
                path = "/api/v2/mix/position/open_positions"
                params = {"marginCoin": "USDT", "api_key": API_KEY, "req_time": int(time.time() * 1000)}
                params['sign'] = sign(params, API_SECRET)
                url = BASE_URL + path
                response = requests.get(url, params=params)
                if response.status_code != 200:
                    return jsonify({"error": f"Status {response.status_code} - {response.text}"}), 500
                resp_json = response.json()
                print(f"📋 Posiciones abiertas: {resp_json}")
                return jsonify(resp_json)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        elif signal == "ENTRY_LONG":
            print("🚀 Entrada LONG")
            # Ejemplo simple de orden compra market
            path = "/api/v1/mix/order/place"
            params = {
                "symbol": real_symbol,
                "price": 0,
                "vol": 1,
                "side": 1,  # 1=buy long
                "type": 1,  # 1=market order
                "open_type": 1,
                "position_id": 0,
                "leverage": 10,
                "external_oid": str(int(time.time() * 1000))
            }
            params['api_key'] = API_KEY
            params['req_time'] = int(time.time() * 1000)
            params['sign'] = sign(params, API_SECRET)
            response = requests.post(BASE_URL + path, json=params)
            resp_json = response.json()
            print(f"🟢 ORDEN BUY → {resp_json}")
            return jsonify(resp_json)

        elif signal == "EXIT_CONFIRMED":
            print("🔄 Señal de cierre recibida.")
            # Llamar endpoint para obtener posición y cerrar
            try:
                path = "/api/v1/mix/position/singlePosition"
                params = {"symbol": real_symbol, "marginCoin": "USDT"}
                params['api_key'] = API_KEY
                params['req_time'] = int(time.time() * 1000)
                params['sign'] = sign(params, API_SECRET)
                url = BASE_URL + path
                response = requests.get(url, params=params)
                if response.status_code != 200:
                    return jsonify({"error": f"Status {response.status_code} - {response.text}"}), 500
                position_info = response.json()
                print(f"📡 Posición obtenida: {position_info}")
                # Aquí agregar lógica para cerrar posición según info recibida
                # Por ejemplo, orden de venta si posición long abierta, etc.
                # Por simplificar, respondemos con la info:
                return jsonify(position_info)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        else:
            return jsonify({"error": "Señal no soportada"}), 400

    except Exception as e:
        print(f"Error en webhook: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
