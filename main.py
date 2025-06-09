import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")
BASE_URL = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

def get_valid_symbol(input_symbol):
    try:
        resp = requests.get(f"{BASE_URL}/api/v2/mix/market/contracts",
                            params={"productType": PRODUCT_TYPE})
        for c in resp.json().get("data", []):
            if c["symbol"].replace("-", "").upper() == input_symbol.upper():
                return c["symbol"]
    except Exception as e:
        print("❌ Error obteniendo contratos:", str(e))
    return None

def auth_headers(method, endpoint, body=""):
    ts = str(int(time.time() * 1000))
    prehash = ts + method.upper() + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def place_order(symbol, side):
    url = "/api/v2/mix/order/place-order"
    body = json.dumps({
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": "1",
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated"
    })
    resp = requests.post(BASE_URL + url,
                         headers=auth_headers("POST", url, body),
                         data=body)
    print(f"🟢 ORDEN {side} → {resp.status_code}, {resp.text}")

def close_positions(symbol):
    print("🔄 Señal de cierre recibida.")
    params = {"symbol": symbol, "marginCoin": MARGIN_COIN}
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    endpoint_base = "/api/v2/mix/position/single-position"
    endpoint_full = f"{endpoint_base}?{qs}"

    headers = auth_headers("GET", endpoint_full)
    resp = requests.get(BASE_URL + endpoint_full, headers=headers)
    print("📊 Respuesta de posición:", resp.json())

    data = resp.json().get("data")
    if not data:
        print("⚠️ No hay posición abierta para cerrar.")
        return

    long_avail = float(data.get("long", {}).get("available", 0))
    short_avail = float(data.get("short", {}).get("available", 0))

    if long_avail > 0:
        print("🔴 Cerrando LONG...")
        place_close_order(symbol, "SELL", long_avail)
    if short_avail > 0:
        print("🔴 Cerrando SHORT...")
        place_close_order(symbol, "BUY", short_avail)

def place_close_order(symbol, side, size):
    url = "/api/v2/mix/order/place-order"
    body = json.dumps({
        "symbol": symbol,
        "marginCoin": MARGIN_COIN,
        "side": side,
        "orderType": "market",
        "size": str(size),
        "timeInForceValue": "normal",
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "reduceOnly": True
    })
    resp = requests.post(BASE_URL + url,
                         headers=auth_headers("POST", url, body),
                         data=body)
    print(f"🔴 ORDEN CIERRE {side} → {resp.status_code}, {resp.text}")

@app.route("/", methods=["POST"])
def webhook():
    data = request.json or {}
    print("📨 Payload recibido:", data)
    signal = data.get("signal")
    raw_symbol = data.get("symbol", "").upper()

    real_symbol = get_valid_symbol(raw_symbol)
    if not real_symbol:
        print(f"❌ Símbolo no válido: {raw_symbol}")
        return "Invalid symbol", 400

    print(f"✅ Símbolo real encontrado: {real_symbol}")

    if signal == "ENTRY_LONG":
        print("🚀 Entrada LONG")
        place_order(real_symbol, "BUY")
    elif signal == "ENTRY_SHORT":
        print("📉 Entrada SHORT")
        place_order(real_symbol, "SELL")
    elif signal and signal.startswith("EXIT"):
        close_positions(real_symbol)
    else:
        print("⚠️ Señal desconocida:", signal)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
