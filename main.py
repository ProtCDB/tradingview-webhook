from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time
import json

app = Flask(__name__)

# ✅ Pega tus claves API aquí (no compartas esto con nadie)
# API_KEY = 'TU_API_KEY'
# API_SECRET = 'TU_API_SECRET'

# CoinEx API endpoint base para futuros (UMCBL = USD-M Contracts)
BASE_URL = "https://api.coinex.com"

# Utilidad para generar firma HMAC-SHA256
def sign_request(params, secret):
    sorted_params = sorted(params.items())
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    sign_str += f"&secret_key={secret}"
    return hashlib.md5(sign_str.encode()).hexdigest().upper()

# Buscar símbolo real (ej. SOLUSDT → SOLUSDT_UMCBL)
def obtener_simbolo_real(symbol):
    r = requests.get(f"{BASE_URL}/perpetual/v1/market/list")
    data = r.json()
    for item in data.get("data", {}).get("market_list", []):
        if item["name"] == symbol:
            return item["symbol"]
    return None

# Crear orden
def crear_orden(symbol, side, size=1, reduce_only=False):
    endpoint = "/perpetual/v1/order/put"
    url = BASE_URL + endpoint
    timestamp = int(time.time() * 1000)

    params = {
        "market": symbol,
        "side": side,  # 1: Buy (Long), 2: Sell (Short)
        "amount": size,
        "price": 0,
        "type": 1,  # 1: Market order
        "open_type": "cross",
        "position_id": 0,
        "leverage": 5,
        "external_oid": str(int(time.time())),
        "reduce_only": int(reduce_only),
        "timestamp": timestamp,
        "api_key": API_KEY,
    }

    params["sign"] = sign_request(params, API_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=params, headers=headers)
    return response.status_code, response.json()

# Cerrar posición si existe
def cerrar_posicion(symbol):
    url = f"{BASE_URL}/perpetual/v1/position/close-position"
    timestamp = int(time.time() * 1000)

    params = {
        "market": symbol,
        "timestamp": timestamp,
        "api_key": API_KEY,
    }

    params["sign"] = sign_request(params, API_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=params, headers=headers)
    return response.status_code, response.json()

@app.route("/", methods=["POST"])
def recibir_senal():
    data = request.get_json()
    print("📨 Payload recibido:", data)

    signal = data.get("signal")
    user_symbol = data.get("symbol", "BTCUSDT")  # Por defecto BTCUSDT
    symbol_real = obtener_simbolo_real(user_symbol)

    if not symbol_real:
        print("❌ Símbolo no encontrado.")
        return jsonify({"error": "Símbolo inválido"}), 400

    print("✅ Símbolo real encontrado:", symbol_real)

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        status, res = crear_orden(symbol_real, side=1, reduce_only=False)

    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        status, res = crear_orden(symbol_real, side=2, reduce_only=False)

    elif signal in ["EXIT_LONG_SL", "EXIT_LONG_TP"]:
        print("🛑 Cierre LONG (SL o TP)")
        status, res = crear_orden(symbol_real, side=2, reduce_only=True)

    elif signal in ["EXIT_SHORT_SL", "EXIT_SHORT_TP"]:
        print("🛑 Cierre SHORT (SL o TP)")
        status, res = crear_orden(symbol_real, side=1, reduce_only=True)

    elif signal == "EXIT_CONFIRMED":
        print("🔄 Señal de cierre recibida.")
        status, res = cerrar_posicion(symbol_real)

    else:
        print("⚠️ Señal desconocida:", signal)
        return jsonify({"error": "Señal no reconocida"}), 400

    print(f"🟢 ORDEN {'BUY' if signal in ['ENTRY_LONG', 'EXIT_SHORT_SL', 'EXIT_SHORT_TP'] else 'SELL'} → {status}, {res}")
    return jsonify({"status": status, "response": res}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
