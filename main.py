import time
import hmac
import hashlib
import logging
import requests
from fastapi import FastAPI, Request
import uvicorn
import os

# Configuración de API Keys (pon tus claves aquí o usa variables de entorno)
API_KEY = os.getenv("BITGET_API_KEY", "TU_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET", "TU_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE", "TU_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

# Setup de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI()

def get_headers(method, path, body=''):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}{method}{path}{body}"
    logger.info(f"Mensaje para firma: {message}")
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    logger.info(f"Firma generada: {signature}")
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def get_open_positions():
    logger.info("Consultando posiciones abiertas...")
    query = "productType=USDT-FUTURES&marginCoin=USDT"
    path = f"/api/v2/mix/position/all-position?{query}"
    url = f"{BASE_URL}{path}"
    headers = get_headers("GET", path)

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["data"]

def close_position(symbol):
    logger.info(f"Intentando cerrar posición para {symbol}...")
    position_side = None
    positions = get_open_positions()

    for pos in positions:
        if pos["symbol"] == symbol and float(pos["total"]) > 0:
            position_side = pos["holdSide"]
            break

    if not position_side:
        return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}

    side = "sell" if position_side == "long" else "buy"

    path = "/api/v2/mix/order/place-order"
    url = BASE_URL + path

    body_data = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "orderType": "market",
        "side": side,
        "size": "100",  # se puede ajustar con la cantidad real
        "productType": "USDT-FUTURES"
    }

    body_json = json.dumps(body_data)
    headers = get_headers("POST", path, body_json)
    response = requests.post(url, headers=headers, data=body_json)
    response.raise_for_status()
    return response.json()

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    if payload.get("signal") == "EXIT_CONFIRMED" and "symbol" in payload:
        symbol = payload["symbol"]
        try:
            result = close_position(symbol)
            return result
        except Exception as e:
            logger.error(f"Excepción general: {e}")
            return {"status": "error", "message": str(e)}
    return {"status": "ignored", "message": "Payload no reconocido"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
