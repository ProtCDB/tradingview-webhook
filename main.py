import os
import hmac
import hashlib
import base64
import time
import json
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import logging

load_dotenv()

# Config
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

# FastAPI app
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Auth headers
def get_headers(method, request_path, body=""):
    timestamp = str(int(time.time() * 1000))
    prehash = timestamp + method.upper() + request_path + body
    sign = hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(sign).decode()

    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

# Obtener posiciones abiertas
def get_open_positions():
    endpoint = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    url = BASE_URL + endpoint
    headers = get_headers("GET", endpoint)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["data"]

# Cerrar una posición
def close_position(symbol, side, size):
    opposite_side = "close_long" if side == "long" else "close_short"
    action = "sell" if side == "long" else "buy"

    endpoint = "/api/v2/mix/order/place-order"
    request_path = "/api/v2/mix/order/place-order"

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": action,
        "orderType": "market",
        "size": size,
        "tradeSide": opposite_side,
        "productType": "USDT-FUTURES"
    }

    body_json = json.dumps(body)
    headers = get_headers("POST", request_path, body_json)
    url = BASE_URL + request_path

    response = requests.post(url, headers=headers, data=body_json)
    response.raise_for_status()
    return response.json()

# Ruta principal
@app.post("/")
async def handle_signal(request: Request):
    data = await request.json()
    signal = data.get("signal")
    symbol = data.get("symbol")

    logger.info(f"📨 Payload recibido: {data}")

    if signal == "EXIT_CONFIRMED":
        try:
            positions = get_open_positions()
            for pos in positions:
                if pos["symbol"] == symbol and float(pos["total"]) > 0:
                    size = pos["total"]
                    side = pos["holdSide"]
                    logger.info(f"✅ Cerrando posición {side} en {symbol} con size {size}")
                    result = close_position(symbol, side, size)
                    logger.info(f"📤 Orden enviada: {result}")
                    return {"status": "closed", "response": result}
            logger.warning(f"⚠️ No hay posición abierta en {symbol}")
            return {"status": "no_position"}
        except Exception as e:
            logger.error(f"❌ Error al cerrar posición: {e}")
            return {"status": "error", "detail": str(e)}

    return {"status": "ignored"}
