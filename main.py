import time
import hmac
import hashlib
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

API_KEY = "tu_api_key_aqui"
API_SECRET = "tu_api_secret_aqui"
API_PASSPHRASE = "tu_passphrase_aqui"
BASE_URL = "https://api.bitget.com"

def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    message = timestamp + method + request_path + body
    signature = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_open_positions():
    timestamp = str(int(time.time() * 1000))
    method = "GET"
    path = "/api/v2/mix/position/all-position"
    # Aquí NO incluimos query params en el mensaje a firmar
    body = ""
    signature = generate_signature(timestamp, method, path, body)

    url = BASE_URL + path
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }

    logger.info("Consultando posiciones abiertas...")
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def close_position(symbol: str):
    timestamp = str(int(time.time() * 1000))
    method = "POST"
    path = "/api/mix/v1/order/close-position"
    body_dict = {
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }
    import json
    body = json.dumps(body_dict)
    signature = generate_signature(timestamp, method, path, body)

    url = BASE_URL + path
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }
    logger.info(f"Intentando cerrar posición para {symbol}...")
    resp = requests.post(url, headers=headers, data=body)
    resp.raise_for_status()
    return resp.json()

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    logger.info(f"📨 Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol")

    if signal != "EXIT_CONFIRMED" or not symbol:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Payload inválido"})

    try:
        positions_response = get_open_positions()
        positions = positions_response.get("data", [])
        # Buscamos la posición abierta para el símbolo
        open_pos = None
        for pos in positions:
            if pos.get("symbol") == symbol:
                open_pos = pos
                break

        if not open_pos:
            return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}

        # Si hay posición abierta, cerramos
        close_resp = close_position(symbol)
        return {"status": "closed", "message": f"Posición en {symbol} cerrada", "close_response": close_resp}

    except requests.HTTPError as e:
        logger.error(f"Error HTTP: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    except Exception as e:
        logger.error(f"Excepción general: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": "Error interno"})

