import os
import time
import hmac
import hashlib
import requests
import logging
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Cambia aquí si tus variables tienen prefijo BITGET_ en Render
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    logger.error("❌ Faltan las variables de entorno BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE")
    raise RuntimeError("Variables de entorno BITGET_API_KEY, BITGET_API_SECRET o BITGET_API_PASSPHRASE no definidas")

BASE_URL = "https://api.bitget.com"

app = FastAPI()

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

def get_open_positions(product_type="UMCBL"):
    timestamp = str(int(time.time() * 1000))
    path = "/api/mix/v1/position/all-position"
    query_string = "?productType=" + product_type
    url = BASE_URL + path + query_string
    headers = sign_request("GET", path + query_string, "", timestamp)
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "00000":
            return data.get("data", [])
        else:
            logger.error(f"Error en get_open_positions: {data}")
            return []
    except Exception as e:
        logger.error(f"❌ Excepción en get_open_positions: {e}")
        return []

def close_position(symbol: str, size: float, hold_side: str):
    timestamp = str(int(time.time() * 1000))
    path = "/api/mix/v1/order/placeOrder"
    url = BASE_URL + path
    body_dict = {
        "symbol": symbol,
        "size": str(size),
        "side": "close_long" if hold_side == "long" else "close_short",
        "type": "market",
        "reduceOnly": True,
        "productType": "UMCBL",
        "marginCoin": "USDT"
    }
    import json
    body = json.dumps(body_dict)
    headers = sign_request("POST", path, body, timestamp)
    try:
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
                        return {"status": "ok", "msg": f"Posición {symbol} cerrada"}
                    else:
                        return {"status": "error", "msg": "No se pudo cerrar posición"}
        logger.warning(f"No hay posición abierta para {symbol} para cerrar")
        return {"status": "error", "msg": "No hay posición abierta para cerrar"}

    return {"status": "error", "msg": "Señal no reconocida"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
