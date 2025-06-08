from flask import Flask, request, jsonify
import requests
import uuid

app = Flask(__name__)

# Configuración de la API de Bitget
API_KEY = 'TU_API_KEY'
API_SECRET = 'TU_API_SECRET'
API_PASSPHRASE = 'TU_PASSPHRASE'
BASE_URL = 'https://api.bitget.com/api/v2'

# Simbolos disponibles (se podría consultar esto desde la API de Bitget)
SYMBOL_MAP = {
    'BTCUSDT': 'BTCUSDT_UMCBL',
    'ETHUSDT': 'ETHUSDT_UMCBL',
    'SOLUSDT': 'SOLUSDT_UMCBL'
    # Añade otros símbolos necesarios
}

def get_valid_symbol(input_symbol):
    return SYMBOL_MAP.get(input_symbol.upper())

def create_order(symbol, side, size):
    endpoint = f"{BASE_URL}/mix/order/place"
    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "side": side,
        "orderType": "market",
        "size": size,
        "tradeSide": "open",
        "clientOid": str(uuid.uuid4()),
        "timeInForceValue": "normal"
    }
    headers = {
        "Content-Type": "application/json",
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": "firma_generada",  # Firma según API Bitget
        "ACCESS-TIMESTAMP": "timestamp",
        "ACCESS-PASSPHRASE": API_PASSPHRASE
    }
    response = requests.post(endpoint, json=body, headers=headers)
    return response.status_code, response.text

def close_position(symbol):
    endpoint = f"{BASE_URL}/mix/order/close-position"
    body = {
        "symbol": symbol,
        "marginCoin": "USDT"
    }
    headers = {
        "Content-Type": "application/json",
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": "firma_generada",
        "ACCESS-TIMESTAMP": "timestamp",
        "ACCESS-PASSPHRASE": API_PASSPHRASE
    }
    response = requests.post(endpoint, json=body, headers=headers)
    return response.status_code, response.text

@app.route('/', methods=['POST'])
def webhook():
    payload = request.get_json()
    print(f"📨 Payload recibido: {payload}")

    signal = payload.get('signal')
    symbol_input = payload.get('symbol', 'BTCUSDT')
    symbol = get_valid_symbol(symbol_input)

    if not symbol:
        print(f"❌ Símbolo no reconocido: {symbol_input}")
        return jsonify({'error': 'Símbolo inválido'}), 400

    print(f"✅ Símbolo real encontrado: {symbol}")

    if signal == 'ENTRY_LONG':
        print("🚀 Entrada LONG")
        status, response = create_order(symbol, 'buy', 0.1)
        print(f"🟢 ORDEN BUY → {status}, {response}")
        return '', 200

    elif signal == 'ENTRY_SHORT':
        print("📊 Entrada SHORT")
        status, response = create_order(symbol, 'sell', 0.1)
        print(f"🔴 ORDEN SELL → {status}, {response}")
        return '', 200

    elif signal == 'EXIT_CONFIRMED':
        print("🔄 Señal de cierre recibida.")
        status, response = close_position(symbol)
        print(f"📊 Respuesta de posición: {response}")
        return '', 200

    else:
        print(f"⚠️ Señal desconocida: {signal}")
        return jsonify({'error': 'Señal desconocida'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=10000, host='0.0.0.0')
