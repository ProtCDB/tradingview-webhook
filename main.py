import time
import hmac
import hashlib
import logging
import os
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configura el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI()

# Variables de entorno desde Render (con prefijo BITGET_)
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

BASE_URL = "https://api.bitget.com"

def sign_request(timestamp, method, path, body=""):
    message = f"{timestamp}{method.upper()}{path}{body}"
    logger.info(f"Mensaje para firma: {message}")
    sign = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    logger.info(f"Firma generada: {sign}")
    return sign

def build_headers(method, path, body=""):
    timestamp = str(int(time.time() * 1000))
    sign = sign_request(timestamp, method, path, body)
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def get_open_positions():
    logger.info("Consultando posiciones abiertas...")
    endpoint = "/api/v2/mix/position/all-position"
    url = f"{BASE_URL}{endpoint}"
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }

    headers = build_headers("GET", endpoint)
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error HTTP: {http_err}, Response content: {response.text}")
    except Exception as e:
        logger.error(f"Error consultando posiciones abiertas: {e}")
    return []

def close_position(symbol, size, hold_side):
    logger.info(f"Intentando cerrar posición para {symbol} ({hold_side}) con size {size}")
    endpoint = "/api/v2/mix/order/place-order"
    url = f"{BASE_URL}{endpoint}"

    order_type = "close_long" if hold_side == "long" else "close_short"

    payload = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": str(size),
        "side": order_type,
        "orderType": "market",
        "productType": "USDT-FUTURES"
    }

    body = json.dumps(payload)
    headers = build_headers("POST", endpoint, body)

    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        logger.info(f"Orden enviada: {response.json()}")
        return True
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error HTTP al cerrar posición: {http_err}, Response content: {response.text}")
    except Exception as e:
        logger.error(f"Error general al cerrar posición: {e}")
    return False

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        positions = get_open_positions()
        matching = [pos for pos in positions if pos.get("symbol") == symbol]

        if matching:
            pos = matching[0]
            size = pos.get("total")
            hold_side = pos.get("holdSide")
            success = close_position(symbol, size, hold_side)

            if success:
                return JSONResponse({"status": "success", "message": f"Posición cerrada: {symbol}"})
            else:
                return JSONResponse({"status": "error", "message": "No se pudo cerrar la posición"}, status_code=500)
        else:
            return JSONResponse({"status": "not_found", "message": f"No hay posición abierta para {symbol}"})
    else:
        return JSONResponse({"status": "ignored", "message": "Señal no válida o incompleta"})
