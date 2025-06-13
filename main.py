import os
import time
import hmac
import hashlib
import logging
from urllib.parse import urlencode
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Cargar variables de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

# Función para firmar requests
def sign_request(timestamp, method, path, query=None, body=""):
    if query:
        query_string = urlencode(query)
        message = f"{timestamp}{method.upper()}{path}?{query_string}"
    else:
        message = f"{timestamp}{method.upper()}{path}{body}"
    logger.info(f"Mensaje para firma: {message}")
    sign = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    logger.info(f"Firma generada: {sign}")
    return sign

# Consultar posiciones abiertas
def get_open_positions():
    logger.info("Consultando posiciones abiertas...")
    endpoint = "/api/v2/mix/position/all-position"
    url = f"{BASE_URL}{endpoint}"
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }

    timestamp = str(int(time.time() * 1000))
    sign = sign_request(timestamp, "GET", endpoint, query=params)
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

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

# Cerrar posición
def close_position(symbol, size, hold_side):
    logger.info(f"Cerrando posición: {symbol}, tamaño: {size}, lado: {hold_side}")
    endpoint = "/api/v2/mix/order/place-order"
    url = f"{BASE_URL}{endpoint}"
    side = "close_long" if hold_side == "long" else "close_short"

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": size,
        "side": side,
        "orderType": "market",
        "productType": "USDT-FUTURES"
    }

    timestamp = str(int(time.time() * 1000))
    body_json = json_dumps(body)
    sign = sign_request(timestamp, "POST", endpoint, body=body_json)
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=body_json)
        response.raise_for_status()
        logger.info(f"Orden de cierre enviada correctamente para {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error cerrando posición para {symbol}: {e}, response: {response.text}")
    return False

# JSON dumps sin espacios ni saltos
def json_dumps(data):
    import json
    return json.dumps(data, separators=(',', ':'))

# Webhook de entrada
@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        positions = get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol and float(pos.get("total", 0)) > 0:
                size = pos.get("total")
                hold_side = pos.get("holdSide")
                success = close_position(symbol, size, hold_side)
                return JSONResponse(content={"status": "success" if success else "fail"})
        return JSONResponse(content={"status": "no_position", "message": f"No hay posición abierta en {symbol}"})
    else:
        return JSONResponse(content={"status": "ignored", "message": "Señal no procesada"})
