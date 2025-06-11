import os
import time
import hmac
import hashlib
import logging
from fastapi import FastAPI, Request
import uvicorn
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

API_BASE = "https://api.bitget.com"
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE")

app = FastAPI()

def get_timestamp():
    return str(int(time.time() * 1000))

def sign(secret, timestamp, method, request_path, body=""):
    # Para GET con query string, request_path incluye query params
    message = timestamp + method.upper() + request_path + body
    hmac_key = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return hmac_key.hexdigest()

def get_headers(method, request_path, body=""):
    timestamp = get_timestamp()
    signature = sign(API_SECRET, timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }
    return headers

def get_open_positions():
    try:
        request_path = "/api/mix/v1/position/all-position"
        query_string = "?productType=UMCBL"
        url = API_BASE + request_path + query_string
        headers = get_headers("GET", request_path + query_string)
        logger.info(f"Consultando posiciones abiertas: {url}")
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "00000":
            return data.get("data", [])
        else:
            logger.error(f"Error en respuesta get_open_positions: {data}")
            return []
    except Exception as e:
        logger.error(f"❌ Excepción en get_open_positions: {e}")
        return []

def close_position(symbol):
    try:
        positions = get_open_positions()
        # Buscar posición abierta para el símbolo dado
        pos = next((p for p in positions if p.get("symbol") == symbol), None)
        if not pos:
            logger.warning(f"No hay posición abierta para {symbol} para cerrar")
            return False

        # Construir payload para cerrar la posición
        body = {
            "symbol": symbol,
            "side": "close_long" if pos.get("holdSide") == "long" else "close_short",
            "marginCoin": "USDT",
            "positionId": pos.get("positionId"),
            "productType": "UMCBL",
            "size": pos.get("available")
        }
        import json
        body_json = json.dumps(body)

        request_path = "/api/mix/v1/order/close-position"
        url = API_BASE + request_path
        headers = get_headers("POST", request_path, body_json)
        logger.info(f"Cerrando posición {symbol} con payload: {body_json}")
        resp = requests.post(url, headers=headers, data=body_json)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Respuesta cerrar posición: {data}")
        return data.get("code") == "00000"
    except Exception as e:
        logger.error(f"❌ Error al cerrar posición: {e}")
        return False

@app.post("/")
async def handle_signal(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")
    signal = payload.get("signal")
    symbol = payload.get("symbol")
    if signal == "EXIT_CONFIRMED":
        success = close_position(symbol)
        if success:
            return {"status": "success", "msg": f"Posición {symbol} cerrada"}
        else:
            return {"status": "error", "msg": "No se pudo cerrar posición"}
    return {"status": "ok", "msg": "Signal no manejado"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
