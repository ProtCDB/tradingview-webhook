import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from bitget.bitget_api import BitgetApi
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

api = BitgetApi(API_KEY, API_SECRET, API_PASSPHRASE)

class SignalPayload(BaseModel):
    signal: str
    symbol: str

def get_open_position(symbol: str):
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }
    try:
        logger.info(f"Parámetro para API: {params} (tipos: {[type(v) for v in params.values()]})")
        response = api.get("/api/v2/mix/position/all-position", params)
        logger.info(f"📊 Respuesta posiciones: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ Error al obtener posiciones: {e}")
        return None

def close_position(symbol: str, side: str, size: str):
    close_side = "sell" if side == "long" else "buy"
    params = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "productType": "USDT-FUTURES",
        "marginMode": "isolated",
        "size": size,
        "side": close_side,
        "orderType": "market"
    }
    try:
        logger.info(f"🛑 Cerrando posición: {params}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden de cierre enviada: {response}")
    except Exception as e:
        logger.error(f"❌ Error al cerrar posición: {e}")

@app.post("/")
async def webhook(payload: SignalPayload):
    logger.info(f"📨 Payload recibido: {payload.dict()}")
    if payload.signal == "EXIT_CONFIRMED":
        logger.info(f"🚨 Intentando cerrar posición para {payload.symbol}...")
        data = get_open_position(payload.symbol)
        if data and data.get("code") == "00000":
            for pos in data.get("data", []):
                if pos.get("symbol") == payload.symbol and float(pos.get("available", 0)) > 0:
                    side = pos.get("holdSide")
                    size = pos.get("available")
                    close_position(payload.symbol, side, size)
                    break
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
