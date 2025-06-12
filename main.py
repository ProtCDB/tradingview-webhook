import os
import time
import hmac
import hashlib
import json
import logging
import requests
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

API_KEY = os.getenv("API_KEY") or os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("API_SECRET") or os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE") or os.getenv("BITGET_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    logger.error("❌ Faltan las variables de entorno API_KEY, API_SECRET o API_PASSPHRASE")
    raise RuntimeError("Variables de entorno API_KEY, API_SECRET o API_PASSPHRASE no definidas")

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

app = FastAPI()

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(method: str, request_path: str, body: str, timestamp: str) -> dict:
    message = timestamp + method.upper() + request_path + body
    signature = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def get_open_positions():
    timestamp = get_timestamp()
    path = "/api/v2/mix/position/all-position"
    url = BASE_URL + path
    headers = sign_request("GET", path, "", timestamp)
    params = {"productType": PRODUCT_TYPE, "marginCoin": MARGIN_COIN}
    logger.info(f"Consultando posiciones abiertas: {url}?{params}")
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception as e:
        logger.error(f"❌ Excepción en get_open_positions: {e}")
        return []

def close_position(symbol: str, size: float, hold_side: str):
    timestamp = get_timestamp()
    path = "/api/v2/mix/order/place-position"
    url = BASE_URL + path
    body_dict = {
        "symbol": symbol,
        "size": str(size),
        "side": "sell" if hold_side == "long" else "buy",
        "tradeSide": "close",
        "orderType": "market",
        "reduceOnly": True,
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "marginCoin": MARGIN_COIN
    }
    body = json.dumps(body_dict)
    headers = sign_request("POST", path, body, timestamp)
    logger.info(f"🔴 Cerrando {hold_side.upper()} {symbol}, size {size}")
    try:
        resp = requests.post(url, headers=headers, data=body)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "00000":
            logger.info("✅ Posición cerrada")
            return True
        logger.error(f"❌ Cierre rechazado: {data}")
        return False
    except Exception as e:
        logger.error(f"❌ Excepción al cerrar posición: {e}")
        return False

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")
    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED":
        positions = get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol:
                size = float(pos.get("total", "0"))
                hold_side = pos.get("holdSide")
                if size > 0:
                    ok = close_position(symbol, size, hold_side)
                    return {"status": "ok" if ok else "error", "msg": "Posición cerrada" if ok else "No se pudo cerrar"}
        logger.warning(f"No hay posición abierta para {symbol}")
        return {"status": "error", "msg": "No hay posición abierta para cerrar"}

    return {"status": "error", "msg": "Señal no reconocida"}
