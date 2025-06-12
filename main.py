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

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    logger.error("❌ Faltan variables BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")
    raise RuntimeError("Variables de entorno Bitget no definidas")

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"  # Debe ir en UPPERCASE según documentación :contentReference[oaicite:1]{index=1}
MARGIN_COIN = "USDT"

app = FastAPI()

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(method: str, path: str, body: str, timestamp: str):
    message = timestamp + method.upper() + path + body
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
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
    params = {"productType": PRODUCT_TYPE, "marginCoin": MARGIN_COIN}
    logger.info(f"Consultando posiciones abiertas: {url}?{params}")
    headers = sign_request("GET", path, "", timestamp)
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])

def close_position(symbol: str, size: float, hold_side: str):
    timestamp = get_timestamp()
    path = "/api/v2/mix/order/place-order"
    url = BASE_URL + path
    side = "close_long" if hold_side == "long" else "close_short"
    body = json.dumps({
        "symbol": symbol,
        "size": str(size),
        "side": side,
        "type": "market",
        "reduceOnly": True,
        "productType": PRODUCT_TYPE,
        "marginCoin": MARGIN_COIN
    })
    logger.info(f"Cerrando {symbol}, side={side}, size={size}")
    headers = sign_request("POST", path, body, timestamp)
    resp = requests.post(url, headers=headers, data=body)
    resp.raise_for_status()
    return resp.json().get("code") == "00000"

@app.post("/")
async def webhook(request: Request):
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
                    return {"status": "ok" if success else "error", "msg": "Cerrada" if success else "No se pudo cerrar"}
        logger.warning(f"No hay posición abierta para {symbol}")
        return {"status": "error", "msg": "No hay posición abierta"}
    return {"status": "error", "msg": "Señal o símbolo no válido"}
