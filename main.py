import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from bitget.bitget_api import BitgetApi

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

def get_valid_symbol(input_symbol):
    # Obtener el símbolo real válido (ej: SOLUSDT_UMCBL)
    try:
        params = {"productType": "USDT-FUTURES"}
        response = api.get("/api/v2/mix/market/contracts", params)
        contracts = response.get("data", [])
        for c in contracts:
            if c["symbol"].startswith(input_symbol):
                return c["symbol"]
    except Exception as e:
        logger.error(f"❌ Error obteniendo contratos: {e}")
    return None

def place_order(symbol: str, side: str, size: str = "1"):
    params = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": side,
        "orderType": "market",
        "size": size,
        "timeInForceValue": "normal",
        "productType": "USDT-FUTURES",
        "marginMode": "isolated"
    }
    try:
        logger.info(f"🟢 Enviando orden {side} para {symbol} con tamaño {size}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden enviada: {response}")
    except Exception as e:
        logger.error(f"❌ Error al enviar orden: {e}")

def get_open_positions(symbol: str):
    params = {
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT"
    }
    try:
        response = api.get("/api/v2/mix/position/all-position", params)
        return response
    except Exception as e:
        logger.error(f"❌ Error al obtener posiciones: {e}")
        return None

def close_position(symbol: str, side: str, size: str):
    # side: "long" o "short" para saber la dirección que tenemos abierta
    close_side = "sell" if side == "long" else "buy"
    params = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "productType": "USDT-FUTURES",
        "marginMode": "isolated",
        "size": size,
        "side": close_side,
        "orderType": "market",
        "reduceOnly": True
    }
    try:
        logger.info(f"🛑 Cerrando posición {side} para {symbol} tamaño {size}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden de cierre enviada: {response}")
    except Exception as e:
        logger.error(f"❌ Error al cerrar posición: {e}")

@app.post("/")
async def webhook(payload: SignalPayload):
    logger.info(f"📨 Payload recibido: {payload.dict()}")
    signal = payload.signal.upper()
    raw_symbol = payload.symbol.upper()

    real_symbol = get_valid_symbol(raw_symbol)
    if not real_symbol:
        logger.error(f"❌ Símbolo no válido: {raw_symbol}")
        return {"status": "error", "detail": "Invalid symbol"}

    # ENTRADAS
    if signal == "ENTRY_LONG":
        place_order(real_symbol, "buy")
    elif signal == "ENTRY_SHORT":
        place_order(real_symbol, "sell")

    # SALIDAS (usar la lógica exit_confirmed para todas las salidas)
    elif signal in ["EXIT_CONFIRMED", "EXIT_LONG_TP", "EXIT_LONG_SL", "EXIT_SHORT_TP", "EXIT_SHORT_SL"]:
        data = get_open_positions(real_symbol)
        if data and data.get("code") == "00000":
            positions = data.get("data", [])
            for pos in positions:
                if pos.get("symbol") == real_symbol and float(pos.get("available", 0)) > 0:
                    side = pos.get("holdSide")  # "long" o "short"
                    size = pos.get("available")
                    close_position(real_symbol, side, size)
                    break
    else:
        logger.warning(f"⚠️ Señal desconocida: {signal}")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
