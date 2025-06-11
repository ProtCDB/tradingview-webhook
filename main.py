from flask import Flask, request, jsonify
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_BASE_URL = "https://api.tu-exchange.com"  # reemplaza por tu endpoint real

if not API_KEY or not API_SECRET:
    app.logger.error("⚠️ API_KEY o API_SECRET no están definidos en variables de entorno")

HEADERS = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def get_open_positions(product_type="USDT-FUTURES"):
    try:
        url = f"{API_BASE_URL}/api/v2/mix/position/all-position?productType={product_type}"
        app.logger.info(f"📡 Consultando posiciones abiertas: {url}")
        response = requests.get(url, headers=HEADERS)
        app.logger.info(f"🔁 Respuesta de posiciones: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        app.logger.error(f"❌ Excepción en get_open_positions: {e}")
        return None

def exit_position(symbol, side):
    try:
        url = f"{API_BASE_URL}/api/v2/mix/order/submit"
        payload = {
            "symbol": symbol,
            "side": "sell" if side == "long" else "buy",
            "positionSide": side,
            "reduceOnly": True,
            "orderType": "market",
            "qty": "1"
        }
        app.logger.info(f"📤 Enviando orden de salida: {payload}")
        response = requests.post(url, headers=HEADERS, json=payload)
        app.logger.info(f"🔁 Respuesta orden: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        app.logger.error(f"❌ Excepción en exit_position: {e}")
        return None

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.json
        app.logger.info(f"📨 Payload recibido: {data}")

        signal = data.get("signal")
        symbol = data.get("symbol", "").upper()

        if signal == "EXIT_CONFIRMED":
            positions = get_open_positions()
            if positions and "data" in positions:
                for pos in positions["data"]:
                    if pos["symbol"] == symbol:
                        side = pos["holdSide"]
                        result = exit_position(symbol, side)
                        if result:
                            return jsonify({"status": "success", "msg": f"Exit confirmado para {symbol}", "result": result})
                        else:
                            return jsonify({"status": "error", "msg": "Error cerrando posición"}), 500
                return jsonify({"status": "error", "msg": f"No hay posición abierta para {symbol}"}), 404
            else:
                return jsonify({"status": "error", "msg": "No se pudieron obtener posiciones abiertas"}), 500

        return jsonify({"status": "error", "msg": "Señal desconocida"}), 400

    except Exception as e:
        app.logger.error(f"❌ Excepción en webhook: {e}")
        return jsonify({"status": "error", "msg": f"Excepción interna: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
