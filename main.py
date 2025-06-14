import os
import logging
import urllib.parse
from fastapi import FastAPI, Request
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("SECRET_KEY")
PASSPHRASE = os.getenv("PASSPHRASE")

bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

@app.post("/")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📨 Payload recibido: {payload}")
        
        signal = payload.get("signal")
        symbol = payload.get("symbol")
        
        if signal == "EXIT_CONFIRMED" and symbol:
            logger.info(f"🚨 Intentando cerrar posición para {symbol}...")
            
            # Parámetros para consultar posiciones abiertas
            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT"
            }
            query_string = urllib.parse.urlencode(params)
            logger.info(f"Parámetro para API: {params}")

            # Petición GET con params en URL
            response = bitget_api.get(f"/api/v2/mix/position/all-position?{query_string}")
            positions = response.get("data", [])

            logger.info(f"Posiciones abiertas: {positions}")

            # Filtrar posición que queremos cerrar
            position_to_close = None
            for pos in positions:
                if pos.get("symbol") == symbol:
                    position_to_close = pos
                    break

            if not position_to_close:
                logger.info(f"No hay posición abierta para {symbol}")
                return {"status": "ok", "message": f"No hay posición abierta para {symbol}"}

            # Aquí cerramos la posición con orden de mercado (market)
            side = "sell" if position_to_close["side"].lower() == "buy" else "buy"
            close_params = {
                "symbol": symbol,
                "side": side,
                "orderType": "market",
                "size": str(position_to_close.get("size", "0")),
                "force": "gtc"
            }
            logger.info(f"Cerrando posición con params: {close_params}")

            close_response = bitget_api.post("/api/v2/mix/order/placeOrder", close_params)
            logger.info(f"Respuesta cierre: {close_response}")

            return {"status": "ok", "message": f"Orden de cierre enviada para {symbol}"}

        else:
            logger.info("Signal no reconocido o símbolo no proporcionado")
            return {"status": "ignored", "message": "Signal no reconocido o símbolo no proporcionado"}

    except BitgetAPIException as e:
        logger.error(f"Error en API Bitget: {e.message}")
        return {"status": "error", "message": e.message}
    except Exception as e:
        logger.error(f"❌ Excepción general: {e}")
        return {"status": "error", "message": str(e)}
