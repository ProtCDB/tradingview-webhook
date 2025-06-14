import os
import logging
from fastapi import FastAPI, Request
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

# ✅ Lógica para obtener posiciones abiertas
def get_open_position(symbol: str):
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }
    try:
        response = api.get("/api/v2/mix/position/all-position", params)
        logger.info(f"📊 Posiciones obtenidas: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ Error al obtener posiciones: {e}")
        return None

# ✅ Cerrar posición simplemente abriendo en sentido opuesto
def exit_position(symbol: str):
    data = get_open_position(symbol)
    if data and data.get("code") == "00000":
        for pos in data.get("data", []):
            if pos.get("symbol") == symbol and float(pos.get("available", 0)) > 0:
                side = pos.get("holdSide")
                size = pos.get("available")
                opposite_side = "sell" if side == "long" else "buy"
                params = {
                    "symbol": symbol,
                    "marginCoin": "USDT",
                    "productType": "USDT-FUTURES",
                    "marginMode": "isolated",
                    "size": size,
                    "side": opposite_side,
                    "orderType": "market"
                }
                try:
                    logger.info(f"🔁 Cerrando posición {side.upper()} con orden {opposite_side.upper()} en {symbol}")
                    response = api.post("/api/v2/mix/order/place-order", params)
                    logger.info(f"✅ Orden de cierre enviada: {response}")
                except Exception as e:
                    logger.error(f"❌ Error cerrando posición: {e}")
                break

# ✅ Entradas long / short
def place_entry_order(symbol: str, direction: str):
    side = "buy" if direction == "long" else "sell"
    params = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "productType": "USDT-FUTURES",
        "marginMode": "isolated",
        "size": "1",
        "side": side,
        "orderType": "market"
    }
    try:
        logger.info(f"🟢 Colocando orden {side.upper()} en {symbol} con params: {params}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden colocada: {response}")
    except Exception as e:
        logger.error(f"❌ Error colocando orden de entrada: {e}")

# ✅ Webhook principal
@app.post("/")
async def webhook(payload: SignalPayload):
    logger.info(f"📨 Payload recibido: {payload.dict()}")

    signal = payload.signal.upper()
    symbol = payload.symbol.upper()

    if signal == "ENTRY_LONG":
        place_entry_order(symbol, "long")
    elif signal == "ENTRY_SHORT":
        place_entry_order(symbol, "short")
    elif signal.startswith("EXIT_"):
        logger.info(f"🚨 Señal de salida: {signal}")
        exit_position(symbol)

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

