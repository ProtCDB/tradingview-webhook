import os
import logging
from fastapi import FastAPI, Request
import requests
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

API_BASE = "https://api.bitget.com"  # Cambia si usas otro endpoint
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE")

app = FastAPI()

def get_headers():
    # Aquí deberías implementar la autenticación según API de Bitget
    # Por simplicidad, pongo un placeholder
    return {
        "Content-Type": "application/json",
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": "SIGNATURE_AQUI",
        "ACCESS-TIMESTAMP": "TIMESTAMP_AQUI",
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
    }

def get_open_positions():
    try:
        url = f"{API_BASE}/api/mix/v1/position/all-position?productType=USDT-FUTURES"
        logger.info(f"Consultando posiciones abiertas: {url}")
        resp = requests.get(url, headers=get_headers())
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception as e:
        logger.error(f"❌ Excepción en get_open_positions: {e}")
        return []

def close_position(symbol: str):
    try:
        # Primero, detectamos la posición abierta para cerrar
        positions = get_open_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)
        if not position:
            logger.warning(f"No hay posición abierta para {symbol} para cerrar")
            return False
        
        side = "sell" if position["holdSide"] == "long" else "buy"
        logger.info(f"Cerrando posición {symbol} lado {side}")

        url = f"{API_BASE}/api/mix/v1/order/placeOrder"
        payload = {
            "symbol": symbol,
            "side": side,
            "orderType": "market",
            "size": str(position["total"]),  # cantidad a cerrar
            "marginCoin": position["marginCoin"],
            "reduceOnly": True,
            "positionSide": "long" if side == "sell" else "short",  # según el lado
        }

        logger.info(f"Payload para cerrar posición: {payload}")
        resp = requests.post(url, json=payload, headers=get_headers())
        resp.raise_for_status()
        logger.info(f"Respuesta cierre: {resp.json()}")
        return True
    except Exception as e:
        logger.error(f"❌ Error al cerrar posición: {e}")
        return False

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    logger.info(f"📨 Payload recibido: {data}")

    signal = data.get("signal")
    symbol = data.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        success = close_position(symbol)
        if success:
            return JSONResponse(content={"status": "ok", "msg": "Posición cerrada"})
        else:
            return JSONResponse(content={"status": "error", "msg": "No se pudo cerrar posición"})
    else:
        logger.warning(f"Señal desconocida o falta símbolo: {signal}")
        return JSONResponse(content={"status": "ignored", "msg": "Señal no manejada"})

