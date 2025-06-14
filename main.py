import os
import logging
from dotenv import load_dotenv
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger('main')

def main():
    # Cargar variables de entorno
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('SECRET_KEY')
    PASSPHRASE = os.getenv('PASSPHRASE')
    DEMO_MODE = os.getenv('DEMO_TRADING', 'false').lower() == 'true'

    bitget = BitgetApi(API_KEY, API_SECRET, PASSPHRASE)

    # Ejemplo payload recibido, en tu caso esto vendrá de tu webhook o entrada real
    payload = {
        'signal': 'EXIT_CONFIRMED',
        'symbol': 'SOLUSDT'
    }

    if payload.get('signal') == 'EXIT_CONFIRMED':
        symbol = payload.get('symbol')
        logger.info(f"📨 Payload recibido: {payload}")
        logger.info(f"🚨 Intentando cerrar posición para {symbol}...")

        try:
            # Consultar posiciones abiertas para USDT-FUTURES
            params = {
                'productType': 'USDT_FUTURES',  # fíjate que en el SDK puede que el guion bajo sea _ y no -
                'marginCoin': 'USDT'
            }
            response = bitget.get('/api/v2/mix/position/all-position', params)

            if response.get('code') == '00000':
                positions = response.get('data', [])
                # Filtrar posiciones para el symbol
                pos_symbol = [p for p in positions if p['symbol'].upper() == symbol.upper()]
                if not pos_symbol:
                    logger.info(f"No hay posición abierta en {symbol}")
                    return

                # Cerrar posición(s)
                for pos in pos_symbol:
                    side_to_close = 'sell' if pos['side'] == 'buy' else 'buy'  # invertimos lado para cerrar
                    order_params = {
                        'symbol': symbol,
                        'side': side_to_close,
                        'orderType': 'market',  # cerrar rápido con orden de mercado
                        'size': str(pos['size']),
                        'marginCoin': 'USDT',
                        'positionId': pos['positionId']
                    }
                    close_response = bitget.post('/api/v2/mix/order/placeOrder', order_params)
                    logger.info(f"Respuesta cierre posición: {close_response}")
            else:
                logger.error(f"Error consultando posiciones: {response}")

        except BitgetAPIException as e:
            logger.error(f"API Exception: {e.message}")
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")

if __name__ == '__main__':
    main()
