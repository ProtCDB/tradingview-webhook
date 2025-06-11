import os
import time
import hmac
import hashlib
import json
import requests
from fastapi import FastAPI, Request
import logging
from typing import Optional

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Bitget API config
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
API_BASE_URL = "https://api.bitget.com"

PRODUCT_TYPE = "USDT-FUTURES"

def generate_signature(timestamp: str, method: str, request_path: str, body: str = ''):
    message = f'{timestamp}{method}{request_path}{body}'
    mac = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return mac.hexdigest()

def bitget_headers(method: str, path: str, body: str = ''):
    timestamp = str(int(time.time() * 1000))
    sign = generate_signature(timestamp, method, path, body)
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def get_open_positions():
    path = f"/api/v2/mix/position/all-position?productType={PRODUCT_TYPE}"
    url = f"{API_BASE_URL}{path}"
    headers = bitget_headers("GET", f"/api/v2/mix/position/all-position?productType={PRODUCT_TYPE}")
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"Error al obtener posiciones: {res.text}")
    return res.json()["data"]

def close_position(symbol: str, margin_coin: str, size: str, hold_side: str):
    path = "/api/v2/mix/order/close-position"
    url = f"{API_BASE_URL}{path}"
    payload = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "holdSide": hold_side
    }
    body = json.dumps(payload)
    headers = bitget_headers("POST", path, body)
    res = requests.post(url, headers=headers, data=body)
    if res.status_code != 200:
        raise Exception(f"Error al cerrar posición: {res.text}")
    return res.json()

@app.post("/")
async def webhook_handler(request: Request):
    payload = await request.json()
    signal = payload.get("signal")
    symbol = payload.get("symbol")

    logging.info(f"📨 Payload recibido: {payload}")

    if signal != "EXIT_CONFIRMED":
        return {"status": "ignorado"}

    try:
        logging.info("📡 Consultando posiciones abiertas")
        positions = get_open_positions()

        target_position = next((p for p in positions if p["symbol"] == symbol and float(p["total"]) > 0), None)
        if not target_position:
            logging.warning(f"⚠️ No se encontró posición abierta para {symbol}")
            return {"status": "sin posición"}

        margin_coin = target_position["marginCoin"]
        size = target_position["total"]
        hold_side = target_position["holdSide"]

        logging.info(f"✅ Cerrando posición: {symbol}, {size}, {hold_side}")
        result = close_position(symbol, margin_coin, size, hold_side)
        logging.info(f"✅ Resultado del cierre: {result}")
        return {"status": "cerrado", "result": result}

    except Exception as e:
        logging.error(f"❌ Error procesando la señal: {str(e)}")
        return {"status": "error", "message": str(e)}
