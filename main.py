import os
import time
import hmac
import hashlib
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Leer credenciales desde variables de entorno (usa prefijos BITGET_)
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

BASE_URL = "https://api.bitget.com"

app = FastAPI()

def sign_request(timestamp, method, path, body=""):
    message = f"{timestamp}{method}{path}{body}"
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    logger.info(f"Mensaje para firma: {message}")
    logger.info(f"Firma generada: {signature}")
    return signature

def get_headers(method, path, body=""):
    timestamp = str(int(time.time() * 1000))
    sign = sign_request(timestamp, method, path, body)
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }
    return headers

def get_open_positions():
    logger.info("Consultando posiciones abiertas...")
    endpoint = "/api/v2/mix/position/all-position"
    url = BASE_URL + endpoint
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }

    headers = get_headers("GET", endpoint)

    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Respuesta posiciones: {data}")
        return data["data"] if data.get("data") else []
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP: {e}, Response content: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error consultando posiciones abiertas: {e}")
        raise

def close_position(symbol, size, hold_side):
    logger.info(f"Cerrando posición: {symbol}, tamaño: {size}, lado: {hold_side}")
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    side = "close_long" if hold_side.lower() == "long" else "close_short"

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": str(size),
        "side": side,
        "orderType": "market",
        "productType": "USDT-FUTURES"
    }

    body_str = json.dumps(body)
    headers = get_headers("POST", endpoint, body_str)

    try:
        resp = requests.post(url, headers=headers, data=body_str)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Orden enviada, respuesta: {result}")
        return result.get("code") == "00000"
    except Exception as e:
        logger.error(f"Error al cerrar posición: {e}")
        return False

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal != "EXIT_CONFIRMED" or not symbol:
        return JSONResponse(content={"status": "ignored", "message": "Señal no válida"}, status_code=200)

    try:
        positions = get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol and float(pos.get("total", 0)) > 0:
                size = pos["total"]
                hold_side = pos["holdSide"]
                success = close_position(symbol, size, hold_side)
                if success:
                    return {"status": "success", "message": f"Posición en {symbol} cerrada correctamente"}
                else:
                    return {"status": "error", "message": "No se pudo cerrar la posición"}
        return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}
    except Exception as e:
        logger.error(f"Excepción general: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
