from flask import Flask, request, jsonify
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException
from dotenv import load_dotenv
import os

# Cargar entorno
load_dotenv(dotenv_path='.env')
env_type = os.getenv('APP_ENV', 'dev')
if env_type == 'production':
    load_dotenv(dotenv_path='.env.production')
else:
    load_dotenv(dotenv_path='.env.dev')

# Flask app
app = Flask(__name__)

# Cierre de posición
def close_position(symbol="SOLUSDT", margin_coin="USDT"):
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('SECRET_KEY')
    PASSPHRASE = os.getenv('PASSPHRASE')

    bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

    try:
        # Obtener posiciones abiertas
        params = {
            "productType": "USDT-FUTURES",
            "marginCoin": margin_coin
        }
        position_data = bitget_api.get("/api/v2/mix/position/all-position", params)

        for pos in position_data.get("data", []):
            if pos["symbol"] == symbol and float(pos["total"]) > 0:
                close_side = "sell" if pos["holdSide"] == "long" else "buy"
                close_order = {
                    "symbol": symbol,
                    "marginCoin": margin_coin,
                    "side": close_side,
                    "size": pos["total"],
                    "price": "",
                    "orderType": "market",
                    "tradeSide": "close",
                    "productType": "USDT-FUTURES"
                }
                response = bitget_api.post("/api/v2/mix/order/place-order", close_order)
                return {"status": "closed", "response": response}

        return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}

    except BitgetAPIException as e:
        return {"status": "error", "message": e.message}

# Endpoint para recibir señal
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    symbol = data.get("symbol", "SOLUSDT")
    signal = data.get("signal", "")

    if signal == "EXIT_CONFIRMED":
        result = close_position(symbol)
        return jsonify(result), 200
    return jsonify({"status": "ignored", "message": "No action taken"}), 200

if __name__ == '__main__':
    app.run(debug=False)
