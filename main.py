import os
import time
import hmac
import hashlib
import requests
from fastapi import FastAPI, Request
import logging
from urllib.parse import urlencode
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET", "").strip()
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

app = FastAPI()

def sign_request(timestamp: str, method: str, request_path: str, body: str = "", params: dict = None) -> str:
    if method.upper() == "GET" and params:
        query = urlencode(params)
        request_path += f"?{query}"
    message = timestamp + method.upper() + request_path + body
    logger.info(f"Mensaje para firma: {message}")
    hmac_key = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    sign = hmac_key.hexdigest()
    logger.info(f"Firma generada: {sign}")
    return sign

def get_open_positions():
    url = "https://api.bitget.com/api/v2/mix/position/all-position"
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }
    method = "GET"
    path = "/api/v2/mix/position/all-position"
    timestamp = str(int(time.time() * 1000))
    body = ""

    sign = sign_request(timestamp, method, path, body, params)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
    }

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        logger.error(f"Error HTTP: {e}, Response content: {response.text}")
        raise

    data = response.json()
    logger.info(f"Posiciones abiertas recibidas: {data}")
    return data.get("data", [])

def close_position(symbol: str, size: float, hold_side: str) -> bool:
    url = "https://api.bitget.com/api/v2/mix/order/place-order"
    method = "POST"
    path = "/api/v2/mix/order/place-order"
    timestamp = str(int(time.time() * 1000))

    side_map = {
        "long": "close_long",
        "short": "close_short"
    }

    if hold_side not in side_map:
        logger.error(f"hold_side desconocido: {hold_side}")
        return False

    body_dict = {
        "symbol": symbol,
        "size": str(size),
        "side": side_map[hold_side],
        "marginCoin": "USDT",
        "orderType": "market"
    }

    body = json.dumps(body_dict)

    sign = sign_request(timestamp, method, path, body)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=body)
    if response.status_code == 200:
        resp_json = response.json()
        if resp_json.get("code") == "00000":
            logger.info(f"✅ Orden de cierre enviada para {symbol}")
            return True
        else:
            logger.error(f"Error en orden de cierre: {resp_json}")
    else:
        logger.error(f"HTTP error {response.status_code}: {response.text}")
    return False

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        logger.info("Consultando posiciones abiertas...")
        try:
            positions = get_open_positions()
        except Exception as e:
            logger.error(f"Error consultando posiciones abiertas: {e}")
            return {"status": "error", "message": "Error consultando posiciones abiertas"}

        for pos in positions:
            if pos.get("symbol") == symbol:
                size = float(pos.get("size", 0))
                hold_side = pos.get("holdSide")
                if size > 0:
                    logger.info(f"Cerrando posición {symbol} de tamaño {size} y lado {hold_side}")
                    success = close_position(symbol, size, hold_side)
                    if success:
                        return {"status": "success", "message": f"Posición {symbol} cerrada"}
                    else:
                        return {"status": "error", "message": "Error cerrando posición"}
        return {"status": "info", "message": "No se encontró posición abierta para el símbolo"}
    else:
        return {"status": "ignored", "message": "Señal o símbolo inválido"}
