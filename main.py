import os
import time
import hmac
import hashlib
import requests
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI()

API_BASE = "https://api.bitget.com"
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

def get_timestamp_ms():
    return str(int(time.time() * 1000))

def get_headers(method: str, request_path: str, body: str = ""):
    timestamp = get_timestamp_ms()
    pre_hash = timestamp + method.upper() + request_path + body
    sign = hmac.new(API_SECRET.encode('utf-8'), pre_hash.encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def get_open_positions():
    try:
        request_path = "/api/mix/v1/position/openPositions"
        url = API_BASE + request_path
        params = {"productType": "UMCBL"}  # Usa "UMCBL" para USDT-margined perpetual futures
        headers = get_headers("GET", request_path)
        logger.info(f"Consultando posiciones abiertas: {url} con params {params}")
        resp = requests.get(url, headers=headers, params=params)
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

def close_position(symbol: str, hold_side: str):
    try:
        request_path = "/api/mix/v1/order/closePosition"
        url = API_BASE + request_path
        body = {
            "symbol": symbol,
            "holdSide": hold_side,  # "long" o "short"
            "marginCoin": "USDT"
        }
        import json
        body_json = json.dumps(body)
        headers = get_headers("POST", request_path, body_json)
        logger.info(f"Cerrando posición: {url} con body {body_json}")
        resp = requests.post(url, headers=headers, data=body_json)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "00000":
            logger.info(f"✅ Posición cerrada correctamente para {symbol}")
            return True
        else:
            logger.error(f"Error cerrando posición: {data}")
            return False
    except Exception as e:
        logger.error(f"❌ Error al cerrar posición: {e}")
        return False

@app.post("/")
async def handle_signal(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        positions = get_open_positions()
        # Buscar posición abierta para ese symbol
        pos = next((p for p in positions if p.get("symbol") == symbol), None)
        if not pos:
            logger.warning(f"No hay posición abierta para {symbol} para cerrar")
            return JSONResponse(content={"status": "error", "msg": "No position open for symbol"}, status_code=200)

        hold_side = pos.get("holdSide")
        if close_position(symbol, hold_side):
            return JSONResponse(content={"status": "success", "msg": f"Position closed for {symbol}"}, status_code=200)
        else:
            return JSONResponse(content={"status": "error", "msg": "No se pudo cerrar posición"}, status_code=200)

    return JSONResponse(content={"status": "error", "msg": "Signal no manejada o falta symbol"}, status_code=400)
