from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')

bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

def safe_post(api, endpoint, params):
    if not isinstance(params, dict):
        logging.warning(f"Parámetros no son dict, se reemplaza por dict vacío: {params}")
        params = {}
    logging.info(f"POST a {endpoint} con params: {params}")
    return api.post(endpoint, params)

def safe_get(api, endpoint, params):
    if not isinstance(params, dict):
        logging.warning(f"Parámetros no son dict, se reemplaza por dict vacío: {params}")
        params = {}
    logging.info(f"GET a {endpoint} con params: {params}")
    return api.get(endpoint, params)

@app.post("/")
async def handle_signal(request: Request):
    payload = await request.json()
    logging.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        logging.info(f"🚨 Intentando cerrar posición para {symbol}...")

        # Ejemplo: consultar posiciones abiertas
        try:
            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT"
            }
            response = safe_get(bitget_api, "/api/v2/mix/position/all-position", params)
            logging.info(f"Posiciones abiertas: {response}")

            # Aquí incluir la lógica para buscar la posición y cerrarla
            # Ejemplo: cerrar posición (placeholder)
            close_params = {
                "symbol": symbol,
                "side": "close",  # Ejemplo, ajustar según API
                "size": "all",    # Ajustar según API
                "orderType": "market"
            }
            close_response = safe_post(bitget_api, "/api/v2/mix/order/placeOrder", close_params)
            logging.info(f"Respuesta cierre posición: {close_response}")

            return JSONResponse(content={"status": "success", "message": f"Posición cerrada para {symbol}", "data": close_response})

        except BitgetAPIException as e:
            logging.error(f"❌ BitgetAPIException: {e.message}")
            return JSONResponse(content={"status": "error", "message": e.message}, status_code=400)
        except Exception as e:
            logging.error(f"❌ Excepción general: {e}")
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

    else:
        return JSONResponse(content={"status": "error", "message": "Signal o symbol no válido"}, status_code=400)
