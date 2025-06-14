import os
import logging
from fastapi import FastAPI, Request
from bitget.bitget_api import BitgetApi

logging.basicConfig(level=logging.INFO)

app = FastAPI()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("SECRET_KEY")
PASSPHRASE = os.getenv("PASSPHRASE")

bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    logging.info(f"📨 Payload recibido: {payload}")

    signal = payload.get("signal")
    symbol = payload.get("symbol")

    if signal == "EXIT_CONFIRMED" and symbol:
        try:
            logging.info(f"🚨 Intentando cerrar posición para {symbol}...")

            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT"
            }

            # Validar que los params sean strings
            for k, v in params.items():
                if not isinstance(v, str):
                    logging.warning(f"Parametro '{k}' no es string, convirtiendo a str.")
                    params[k] = str(v)
                logging.info(f"Parámetro para API: {k} = {params[k]} (tipo: {type(params[k])})")

            response = bitget_api.get("/api/v2/mix/position/all-position", params)
            logging.info(f"Respuesta posiciones abiertas: {response}")

            # Aquí implementar la lógica para cerrar posiciones que coincidan con symbol
            # Ejemplo:
            for pos in response.get("data", []):
                if pos.get("symbol") == symbol:
                    # Ejemplo simple para cerrar posición: llamar a bitget_api.post(...)
                    # Ajustar según doc oficial y lógica que quieras
                    close_params = {
                        "symbol": symbol,
                        "side": "close",  # verificar el valor correcto
                        "size": pos.get("size"),
                        # otros campos que la API requiera
                    }
                    logging.info(f"Intentando cerrar posición con params: {close_params}")
                    close_resp = bitget_api.post("/api/v2/mix/order/close-position", close_params)
                    logging.info(f"Respuesta cierre posición: {close_resp}")
                    return {"status": "success", "message": f"Posición cerrada para {symbol}"}

            return {"status": "error", "message": f"No se encontró posición abierta para {symbol}"}

        except Exception as e:
            logging.error(f"❌ Excepción general: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "Signal o symbol no proporcionado"}
