from fastapi import FastAPI, Request
from dotenv import load_dotenv
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Cargar .env según entorno
env_type = os.getenv('APP_ENV', 'dev')
if env_type == 'production':
    load_dotenv('.env.production')
else:
    load_dotenv('.env.dev')

# Inicializar FastAPI
app = FastAPI()

# Cargar claves
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')
demo_mode = os.getenv("DEMO_TRADING", "false").lower() == "true"

# Inicializar cliente Bitget
bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

@app.post("/")
async def recibir_senal(request: Request):
    payload = await request.json()
    logger.info(f"📨 Payload recibido: {payload}")

    symbol = payload.get("symbol")
    signal = payload.get("signal")

    if signal == "EXIT_CONFIRMED":
        logger.info(f"🚨 Intentando cerrar posición para {symbol}...")
        try:
            response = bitget_api.get(
                "/api/v2/mix/position/all-position",
                {
                    "productType": "USDT-FUTURES",
                    "marginCoin": "USDT"
                }
            )
            logger.info(f"✅ Respuesta de posiciones abiertas: {response}")
            # Aquí se podría analizar la posición y ejecutar una orden de cierre si existe

            return {"status": "ok", "detalle": "Consulta completada", "response": response}
        except BitgetAPIException as e:
            logger.error(f"❌ Bitget API Error: {e.message}")
            return {"status": "error", "detalle": e.message}
        except Exception as e:
            logger.error(f"❌ Excepción general: {str(e)}")
            return {"status": "error", "detalle": str(e)}

    return {"status": "ignored", "detalle": "No es una señal de salida"}
