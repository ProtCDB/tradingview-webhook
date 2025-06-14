import time
import hmac
import hashlib
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Configura el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Credenciales reales Bitget
API_KEY = "TU_API_KEY"
API_SECRET = "TU_API_SECRET"
PASSPHRASE = "TU_PASSPHRASE"
BASE_URL = "https://api.bitget.com"

HEADERS_BASE = {
    "Content-Type": "application/json",
    "ACCESS-KEY": API_KEY,
    "ACCESS-PASSPHRASE": PASSPHRASE
}

def generar_firma(timestamp, metodo, request_path, cuerpo=""):
    mensaje = f"{timestamp}{metodo}{request_path}{cuerpo}"
    firma = hmac.new(API_SECRET.encode(), mensaje.encode(), hashlib.sha256).hexdigest()
    return firma

def obtener_posiciones():
    try:
        timestamp = str(int(time.time() * 1000))
        metodo = "GET"
        request_path = "/api/v2/mix/position/all-position"
        query_string = "productType=USDT-FUTURES&marginCoin=USDT"
        url = f"{BASE_URL}{request_path}?{query_string}"
        
        firma = generar_firma(timestamp, metodo, request_path)
        
        headers = {
            **HEADERS_BASE,
            "ACCESS-SIGN": firma,
            "ACCESS-TIMESTAMP": timestamp
        }

        logger.info(f"🔑 Firma generada: {firma}")
        respuesta = requests.get(url, headers=headers)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error HTTP: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Excepción general: {e}")
        raise

def cerrar_posicion(symbol):
    posiciones = obtener_posiciones()

    for pos in posiciones.get("data", []):
        if pos.get("symbol") == symbol and float(pos.get("total")) != 0:
            lado = "close_long" if pos["holdSide"] == "long" else "close_short"
            size = pos["total"]
            
            timestamp = str(int(time.time() * 1000))
            metodo = "POST"
            request_path = "/api/v2/mix/order/close-position"
            url = BASE_URL + request_path

            cuerpo = {
                "symbol": symbol,
                "marginCoin": "USDT",
                "holdSide": pos["holdSide"]
            }

            import json
            cuerpo_json = json.dumps(cuerpo, separators=(',', ':'))
            firma = generar_firma(timestamp, metodo, request_path, cuerpo_json)

            headers = {
                **HEADERS_BASE,
                "ACCESS-SIGN": firma,
                "ACCESS-TIMESTAMP": timestamp
            }

            logger.info(f"📤 Cerrando posición: {cuerpo}")
            respuesta = requests.post(url, headers=headers, json=cuerpo)
            respuesta.raise_for_status()
            return {"status": "success", "data": respuesta.json()}
    
    return {"status": "no_position", "message": f"No hay posición abierta en {symbol}"}

@app.post("/")
async def recibir_senal(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        logger.info(f"🚨 Intentando cerrar posición para {symbol}...")
        try:
            resultado = cerrar_posicion(symbol)
            return JSONResponse(content=resultado)
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    
    return JSONResponse(content={"status": "ignored", "message": "Señal no reconocida"})
