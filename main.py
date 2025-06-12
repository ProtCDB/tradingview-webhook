import os
import time
import hmac
import hashlib
import logging
import requests
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Variables de entorno con prefijo BITGET_
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    logger.error("❌ Faltan las variables de entorno BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")
    raise RuntimeError("Variables de entorno Bitget no definidas")

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "umcbl"
MARGIN_COIN = "USDT"

app = FastAPI()

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(method, path, body, timestamp):
    message = f"{timestamp}{method.upper()}{path}{body}"
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
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
        timestamp = get_timestamp()
        path = "/api/v2/mix/position/all-position"
        params = {
            "productType": PRODUCT_TYPE,
            "marginCoin": MARGIN_COIN
        }
        url = f"{BASE_URL}{path}"
        logger.info(f"Consultando posiciones abiertas: {url}?{params}")
        headers = sign_request("GET", path, "", timestamp)
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception as e:
        logger.error(f"❌ Excepción en get_open_positions: {e}")
        return []

def close_position(symbol, size, hold_side):
    try:
        timestamp = get_timestamp()
        path = "/api/v2/mix/order/place-order"
        url = f"{BASE_URL}{path}"
        body_dict = {
            "symbol": symbol,
            "size": str(size),
            "side": "close_long" if hold_side == "long" else "close_short",
            "type": "market",
            "reduceOnly": True,
            "productType": PRODUCT_TYPE,
            "marginCoin": MARGIN_COIN
        }
        import json
        body = json.dumps(body_dict)
        headers = sign_request("POST", path, body, timestamp)
        logger.info(f"Cerrando posición {symbol} con payload: {body}")
        resp = requests.post(url, headers=headers, data=body)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Respuesta al cerrar posición: {data}")
        return data.get("code") == "00000"
    except Exception as e:
        logger.error(f"❌ Excepción al cerrar posición: {e}")
        return False

@app.post("/")
async def handle_webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        positions = get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol:
                size = float(pos.get("total", "0"))
                hold_side = pos.get("holdSide")
                if size > 0 and hold_side:
                    success = close_position(symbol, size, hold_side)
                    if success:
                        return {"status": "ok", "msg": f"Posición {symbol} cerrada"}
                    else:
                        return {"status": "error", "msg": "No se pudo cerrar posición"}
        logger.warning(f"No hay posición abierta para {symbol}")
        return {"status": "error", "msg": "No hay posición abierta para cerrar"}

    return {"status": "error", "msg": "Señal o símbolo no válido"}
