import os
import time
import hmac
import hashlib
import json
import logging
import requests
from fastapi import FastAPI, Request

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Carga de variables de entorno
API_KEY = os.getenv("API_KEY") or os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("API_SECRET") or os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE") or os.getenv("BITGET_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    logger.error("❌ Faltan las variables de entorno API_KEY, API_SECRET o API_PASSPHRASE")
    raise RuntimeError("Variables de entorno API_KEY, API_SECRET o API_PASSPHRASE no definidas")

BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "UMCBL"

app = FastAPI()

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(method: str, request_path: str, body: str, timestamp: str) -> dict:
    message = timestamp + method.upper() + request_path + body
    signature = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }
    return headers

def get_open_positions(product_type=PRODUCT_TYPE):
    timestamp = get_timestamp()
    path = "/api/mix/v1/position/all-position"
    url = BASE_URL + path
    headers = sign_request("GET", path, "", timestamp)
    params = {"productType": product_type}
    logger.info(f"Consultando posiciones abiertas: {url}?productType={product_type}")
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
    path = "/api/mix/v1/order/placeOrder"
    url = BASE_URL + path
    body_dict = {
        "symbol": symbol,
        "size": str(size),
        "side": "close_long" if hold_side == "long" else "close_short",
        "type": "market",
        "reduceOnly": True,
        "productType": PRODUCT_TYPE,
        "marginCoin": "USDT"
    }
    body = json.dumps(body_dict)
    headers = sign_request("POST", path, body, timestamp)
    try:
        logger.info(f"Cerrando posición con payload: {body}")
        resp = requests.post(url, headers=headers, data=body)
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json.get("code") == "00000":
            logger.info(f"✅ Posición cerrada correctamente para {symbol}")
            return True
        else:
            logger.error(f"❌ Error al cerrar posición: {resp_json}")
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
    if not signal or not symbol:
        return {"status": "error", "msg": "Faltan signal o symbol"}

    if signal == "EXIT_CONFIRMED":
        positions = get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol:
                size = float(pos.get("total", "0"))
                hold_side = pos.get("holdSide")
                if size > 0:
                    if close_position(symbol, size, hold_side):
                        return {"status": "ok", "msg": "Posición cerrada"}
                    else:
                        return {"status": "error", "msg": "No se pudo cerrar posición"}
        logger.warning(f"No hay posición abierta para {symbol} para cerrar")
        return {"status": "error", "msg": "No hay posición abierta para cerrar"}

    return {"status": "error", "msg": "Señal no reconocida"}
