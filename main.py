from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException
from dotenv import load_dotenv
import os
import time

# Cargar variables de entorno
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')
DEMO_MODE = os.getenv('DEMO_TRADING', 'false').lower() == 'true'

bitget_api = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

def cerrar_posicion(symbol):
    try:
        print(f"🔍 Consultando posiciones abiertas para {symbol}...")
        response = bitget_api.get('/api/v2/mix/position/single-position', {
            "symbol": symbol,
            "marginCoin": "USDT"
        })

        position_data = response.get('data', {})
        total = float(position_data.get('total', 0))

        if total == 0:
            print("✅ No hay posición abierta.")
            return

        hold_side = position_data.get('holdSide')
        side = 'sell' if hold_side == 'long' else 'buy'

        close_params = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": str(total),
            "side": side,
            "orderType": "market",
            "force": "gtc"
        }

        print(f"🚨 Cerrando posición {hold_side} de {total} {symbol} con {side.upper()}...")
        close_response = bitget_api.post('/api/v2/mix/order/place-order', close_params)
        print(f"📤 Orden enviada: {close_response}")

    except BitgetAPIException as e:
        print("❌ Error Bitget:", e.message)
    except Exception as e:
        print("❌ Error general:", str(e))

if __name__ == '__main__':
    cerrar_posicion("SOLUSDT")
