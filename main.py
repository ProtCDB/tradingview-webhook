import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from bitget.bitget_api import BitgetApi  # Asumo tu cliente API personalizado

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

def place_order(symbol: str, side: str):
    params = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "productType": "USDT-FUTURES",
        "marginMode": "isolated",
        "size": "1",
        "side": side.lower(),  # "buy" o "sell"
        "orderType": "market"
    }
    try:
        logger.info(f"🟢 Colocando orden {side.upper()} en {symbol} con params: {params}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden colocada: {response}")
    except Exception as e:
        logger.error(f"❌ Error colocando orden: {e}")

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
        logger.error(f"❌ Error obteniendo posiciones: {e}")
        return None

def close_position(symbol: str, side: str, size: str):
    # Para cerrar LONG, enviamos una orden SELL; para cerrar SHORT, enviamos BUY
    close_side = "sell" if side.lower() == "long" else "buy"
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
        logger.info(f"🛑 Cerrando posición {side.upper()} con orden {close_side.upper()} tamaño {size} en {symbol}")
        response = api.post("/api/v2/mix/order/place-order", params)
        logger.info(f"✅ Orden de cierre enviada: {response}")
    except Exception as e:
        logger.error(f"❌ Error cerrando posición: {e}")

@app.post("/")
async def webhook(payload: SignalPayload):
    logger.info(f"📨 Payload recibido: {payload.dict()}")
    symbol = payload.symbol.upper()
    signal = payload.signal.lower()

    if signal == "entry_long":
        place_order(symbol, "buy")

    elif signal == "entry_short":
        place_order(symbol, "sell")

    elif signal in ["exit_confirmed", "exit_long_tp", "exit_long_sl", "exit_short_tp", "exit_short_sl"]:
        positions_data = get_open_position(symbol)
        if positions_data and positions_data.get("code") == "00000":
            for pos in positions_data.get("data", []):
                if pos.get("symbol") == symbol and float(pos.get("available", 0)) > 0:
                    side = pos.get("holdSide")  # "long" o "short"
                    size = pos.get("available")
                    close_position(symbol, side, size)
                    break
        else:
            logger.warning(f"⚠️ No posiciones abiertas o error obteniendo posiciones para {symbol}")

    else:
        logger.warning(f"⚠️ Señal desconocida: {signal}")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
