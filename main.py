import os
import logging
from bitget.bitget_api import BitgetApi
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

app = FastAPI()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')

bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

def safe_str_dict(d):
    return {str(k): str(v) if v is not None else "" for k, v in d.items()}

@app.post("/")
async def handle_signal(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    if payload.get("signal") == "EXIT_CONFIRMED":
        symbol = payload.get("symbol")
        if not symbol:
            return {"status": "error", "message": "symbol is required"}

        try:
            logger.info(f"🚨 Intentando cerrar posición para {symbol}...")

            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
            }
            params = safe_str_dict(params)
            logger.info(f"Parámetro para API: {params}")

            response = bitget_api.get("/api/v2/mix/position/all-position", params)
            logger.debug(f"Respuesta all-position: {response}")

            # Buscar posición abierta para el símbolo
            positions = response.get("data", [])
            position_to_close = None
            for pos in positions:
                if pos.get("symbol") == symbol:
                    position_to_close = pos
                    break

            if not position_to_close:
                return {"status": "error", "message": f"No open position found for {symbol}"}

            side = "close_long" if position_to_close.get("positionSide") == "long" else "close_short"

            close_params = {
                "symbol": symbol,
                "side": side,
                "orderType": "market",
                "size": position_to_close.get("available"),
                "reduceOnly": True,
            }
            close_params = safe_str_dict(close_params)
            logger.info(f"Parámetros para cerrar posición: {close_params}")

            close_response = bitget_api.post("/api/mix/v1/order/placeOrder", close_params)
            logger.info(f"Respuesta cierre posición: {close_response}")

            return {"status": "success", "close_response": close_response}

        except Exception as e:
            logger.error(f"❌ Excepción general: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "ignored", "message": "Signal not handled"}
