import os
from fastapi import FastAPI, Request
from bitget.bitget_api import BitgetApi
from bitget.exceptions import BitgetAPIException

app = FastAPI()

API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')

bitget_api = BitgetApi(API_KEY, SECRET_KEY, PASSPHRASE)

@app.post("/")
async def handle_signal(request: Request):
    data = await request.json()
    symbol = data.get('symbol')
    signal = data.get('signal')

    print(f"📨 Payload recibido: {data}")

    if signal == "EXIT_CONFIRMED" and symbol:
        try:
            print(f"🚨 Intentando cerrar posición para {symbol}...")

            # Paso 1: Consultar posiciones abiertas para ese símbolo
            params = {
                "productType": "UMCBL",  # Ajusta según tu producto (ej: USDT-FUTURES, UMCBL)
                "marginCoin": "USDT"
            }
            resp = bitget_api.get("/api/v2/mix/position/all-position", params)
            positions = resp.get('data', [])

            # Buscar posición abierta para el símbolo
            open_position = None
            for pos in positions:
                if pos.get('symbol') == symbol:
                    open_position = pos
                    break
            
            if not open_position:
                return {"status": "no_position", "message": f"No hay posición abierta para {symbol}"}

            size = open_position.get('available')
            side = open_position.get('side')  # LONG o SHORT

            if float(size) <= 0:
                return {"status": "no_position", "message": f"Posición abierta de tamaño cero para {symbol}"}

            # Paso 2: Enviar orden para cerrar la posición
            # Para cerrar LONG, vendemos (side='sell'), para cerrar SHORT, compramos (side='buy')
            close_side = 'sell' if side.upper() == 'LONG' else 'buy'

            order_params = {
                "symbol": symbol,
                "side": close_side,
                "orderType": "market",
                "size": size,
                "force": "normal",
                "productType": "UMCBL",
                "marginCoin": "USDT"
            }
            order_resp = bitget_api.post("/api/v2/mix/order/placeOrder", order_params)

            print(f"Orden de cierre enviada: {order_resp}")

            return {"status": "success", "message": f"Orden de cierre enviada para {symbol}", "order_response": order_resp}

        except BitgetAPIException as e:
            return {"status": "error", "message": f"Bitget API error: {e.message}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "error", "message": "Signal no reconocido o símbolo faltante"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
