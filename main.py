import os
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from bitget.bitget_api import BitgetApi
from fastapi.responses import JSONResponse

# Configuración de logs
logging.basicConfig(level=logging.INFO)

# Inicializar FastAPI
app = FastAPI()

# Inicializar Bitget API con claves del entorno
api_key = os.getenv("BITGET_API_KEY")
api_secret = os.getenv("BITGET_API_SECRET")
passphrase = os.getenv("BITGET_API_PASSPHRASE")

bitget_api = BitgetApi(api_key, api_secret, passphrase)

# Modelo del cuerpo esperado
class SignalRequest(BaseModel):
    signal: str
    symbol: str

# Ruta principal (solo POST)
@app.post("/")
async def recibir_senal(data: SignalRequest):
    logging.info(f"📨 Payload recibido: {data.dict()}")

    if data.signal == "EXIT_CONFIRMED":
        logging.info(f"🚨 Intentando cerrar posición para {data.symbol}...")
        resultado = cerrar_posicion(bitget_api, data.symbol)
        return JSONResponse(content={"status": "ok", "resultado": resultado})

    return JSONResponse(content={"status": "ignorado", "mensaje": "Señal no manejada"})


def cerrar_posicion(bitget_api, symbol):
    try:
        product_type = "USDT-FUTURES"
        margin_coin = "USDT"

        # Asegurarse de que los parámetros sean strings
        params = {
            "productType": str(product_type),
            "marginCoin": str(margin_coin)
        }

        logging.info(f"Parámetro para API: {params} (tipos: {[type(v) for v in params.values()]})")

        # Obtener todas las posiciones abiertas
        response = bitget_api.get("/api/v2/mix/position/all-position", params)

        logging.info(f"📊 Respuesta posiciones: {response}")
        return response

    except Exception as e:
        logging.error(f"❌ Excepción general: {e}")
        return {"error": str(e)}
