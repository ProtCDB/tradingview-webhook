import logging
from fastapi import FastAPI
from pydantic import BaseModel
from bitget_api import BitgetRestClient, APIRequestError
import uuid
import os

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

client = BitgetRestClient(api_key=API_KEY, api_secret=API_SECRET, passphrase=API_PASSPHRASE)

class SignalPayload(BaseModel):
    signal: str
    symbol: str

def generate_client_oid():
    return str(uuid.uuid1())

def get_position(symbol: str):
    try:
        response = client.positions_api.get_position(symbol=symbol, product_type="USDT-FUTURES")
        logger.info(f"📊 Posiciones obtenidas: {response}")
        return response
    except APIRequestError as e:
        logger.error(f"❌ Error al obtener la posición: {e}")
        return None

def place_order(symbol: str, side: str, size: str):
    margin_coin = "USDT"
    params = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "productType": "USDT-FUTURES",
        "marginMode": "isolated",
        "size": size,
        "side": side,
        "orderType": "market"
    }
    logger.info(f"🟢 Colocando orden {side.upper()} en {symbol} con params: {params}")
    try:
        response = client.trade_api.place_order(**params)
        logger.info(f"✅ Orden colocada: {response}")
        return response
    except APIRequestError as e:
        logger.error(f"❌ Error colocando orden de entrada: {e}")
        return None

@app.post("/")
async def handle_signal(payload: SignalPayload):
    signal = payload.signal.upper()
    symbol = payload.symbol.upper()
    logger.info(f"📨 Payload recibido: {{'signal': '{signal}', 'symbol': '{symbol}'}}")

    if signal == "ENTRY_LONG":
        return place_order(symbol, side="buy", size="1")

    elif signal == "ENTRY_SHORT":
        return place_order(symbol, side="sell", size="1")

    elif signal in ["EXIT_CONFIRMED", "EXIT_SHORT_TP", "EXIT_LONG_TP", "EXIT_SHORT_SL", "EXIT_LONG_SL"]:
        logger.info(f"🚨 Señal de salida recibida: {signal}")
        position_data = get_position(symbol)

        if not position_data or not position_data.get("data"):
            logger.warning("⚠️ No hay datos de posición para cerrar.")
            return {"status": "no_position"}

        position = position_data["data"][0]
        size = position.get("available", "0")
        hold_side = position.get("holdSide")

        if hold_side == "long":
            logger.info(f"🛑 Cerrando posición LONG con orden SELL tamaño {size} en {symbol} (motivo: {signal})")
            return place_order(symbol, side="sell", size=size)

        elif hold_side == "short":
            logger.info(f"🔁 Cerrando posición SHORT con orden BUY tamaño {size} en {symbol} (motivo: {signal})")
            return place_order(symbol, side="buy", size=size)

        else:
            logger.warning("⚠️ No hay posición abierta para cerrar.")
            return {"status": "no_position"}

    else:
        logger.warning(f"⚠️ Señal no reconocida: {signal}")
        return {"status": "unknown_signal"}
