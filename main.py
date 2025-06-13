import os
import time
import hmac
import hashlib
import json
import logging
import requests
from urllib.parse import urlencode, quote
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Cargar credenciales desde entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"

# Firma de solicitud
def sign_request(timestamp, method, path, body="", params=None):
    if method.upper() == "GET" and params:
        query = urlencode(params, quote_via=quote)
        path += f"?{query}"
    message = f"{timestamp}{method.upper()}{path}{body}"
    logger.info(f"Mensaje para firma: {message}")
    sign = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    logger.info(f"Firma generada: {sign}")
    return sign

# Construir headers autenticados
def build_headers(method, path, body="", params=None):
    timestamp = str(int(time.time() * 1000))
    sign = sign_request(timestamp, method, path, body, params)
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

# Obtener posiciones abiertas
def get_open_positions():
    logger.info("Consultando posiciones abiertas...")
    path = "/api/v2/mix/position/all-position"
    params = {"productType": "USDT-FUTURES", "marginCoin": "USDT"}
    headers = build_headers("GET", path, params=params)
    try:
        response = requests.get(BASE_URL + path, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("positions", [])
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP: {e}, Response content: {e.response.text}")
    except Exception as e:
        logger.error(f"Error consultando posiciones abiertas: {e}")
    return []

# Cerrar posición
def close_position(symbol, size, hold_side):
    logger.info(f"⛔ Cerrando posición {symbol} [{hold_side}] tamaño: {size}")
    path = "/api/v2/mix/order/place-order"
    side = "close_long" if hold_side == "long" else "close_short"
    body_data = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": size,
        "side": side,
        "orderType": "market",
        "productType": "USDT-FUTURES"
    }
    body_json = json.dumps(body_data, separators=(",", ":"))
    headers = build_headers("POST", path, body=body_json)
    try:
        response = requests.post(BASE_URL + path, headers=headers, data=body_json)
        response.raise_for_status()
        logger.info(f"✅ Orden enviada: {response.json()}")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Error al cerrar posición: {e}, Response: {e.response.text}")
    return False

# App FastAPI
app = FastAPI()

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal != "EXIT_CONFIRMED" or not symbol:
        return JSONResponse({"status": "ignored", "message": "Señal inválida"})

    positions = get_open_positions()
    for pos in positions:
        if pos.get("symbol") == symbol and float(pos.get("total", 0)) > 0:
            success = close_position(symbol, pos["total"], pos["holdSide"])
            if success:
                return {"status": "ok", "message": f"Posición en {symbol} cerrada"}
            else:
                return {"status": "error", "message": "No se pudo cerrar la posición"}

    return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}
