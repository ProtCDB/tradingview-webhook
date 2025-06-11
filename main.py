from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_BASE_URL = "https://api.tu-exchange.com"  # Cambia al endpoint real

HEADERS = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def get_open_positions(product_type="USDT-FUTURES"):
    url = f"{API_BASE_URL}/api/v2/mix/position/all-position?productType={product_type}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        app.logger.error(f"Error listando posiciones: {response.status_code} - {response.text}")
        return None

def exit_position(symbol, side):
    # Construye la orden de salida con los datos necesarios
    url = f"{API_BASE_URL}/api/v2/mix/order/submit"
    payload = {
        "symbol": symbol,
        "side": "sell" if side == "long" else "buy",
        "positionSide": side,
        "reduceOnly": True,
        "orderType": "market",
        "qty": "1"  # Ajusta cantidad según necesidad o posición abierta
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        app.logger.error(f"Error cerrando posición: {response.status_code} - {response.text}")
        return None

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    app.logger.info(f"Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol", "").upper()

    if signal == "EXIT_CONFIRMED":
        # Buscamos las posiciones abiertas para validar
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
