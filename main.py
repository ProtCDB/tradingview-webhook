from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_KEY = 'TU_API_KEY'  # ← tus claves ya estaban bien
API_SECRET = 'TU_API_SECRET'
BASE_URL = 'https://api.bingx.com'

HEADERS = {
    'X-BX-APIKEY': API_KEY,
    'Content-Type': 'application/json'
}

def get_real_symbol(symbol):
    if not symbol.endswith('_UMCBL'):
        symbol += '_UMCBL'
    return symbol

def create_order(symbol, side, positionSide):
    url = f'{BASE_URL}/openApi/swap/v2/trade/order'
    body = {
        "symbol": symbol,
        "price": "",
        "vol": "0.01",  # Ajusta tu tamaño de orden si es necesario
        "side": side,
        "type": "market",
        "openType": "isolated",
        "positionSide": positionSide,
        "leverage": "5",
        "externalOid": f"{positionSide.lower()}_entry"
    }

    response = requests.post(url, headers=HEADERS, json=body)
    return response.status_code, response.text

def close_position(symbol, positionSide):
    url = f'{BASE_URL}/openApi/swap/v2/trade/close-position'
    body = {
        "symbol": symbol,
        "positionSide": positionSide,
        "marginCoin": "USDT"
    }

    response = requests.post(url, headers=HEADERS, json=body)
    return response.status_code, response.text

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    signal = data.get('signal')
    symbol = data.get('symbol', 'BTCUSDT')

    print(f"📨 Payload recibido: {data}")

    real_symbol = get_real_symbol(symbol)
    print(f"✅ Símbolo real encontrado: {real_symbol}")

    if signal == 'ENTRY_LONG':
        print("🚀 Entrada LONG")
        status, res = create_order(real_symbol, side='BUY', positionSide='LONG')
        print(f"🟢 ORDEN BUY → {status}, {res}")

    elif signal == 'ENTRY_SHORT':
        print("🔻 Entrada SHORT")
        status, res = create_order(real_symbol, side='SELL', positionSide='SHORT')
        print(f"🔴 ORDEN SELL → {status}, {res}")

    elif signal in ['EXIT_LONG_TP', 'EXIT_LONG_SL']:
        print("📉 Salida LONG (TP o SL)")
        status, res = close_position(real_symbol, positionSide='LONG')
        print(f"🟡 CERRAR LONG → {status}, {res}")

    elif signal in ['EXIT_SHORT_TP', 'EXIT_SHORT_SL']:
        print("📈 Salida SHORT (TP o SL)")
        status, res = close_position(real_symbol, positionSide='SHORT')
        print(f"🔵 CERRAR SHORT → {status}, {res}")

    elif signal == 'EXIT_CONFIRMED':
        print("🔄 Señal de cierre recibida.")
        for pos in ['LONG', 'SHORT']:
            status, res = close_position(real_symbol, positionSide=pos)
            print(f"⚪️ CERRAR {pos} → {status}, {res}")

    else:
        print(f"❓ Señal desconocida: {signal}")
        return jsonify({'error': 'Señal desconocida'}), 400

    return jsonify({'success': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
