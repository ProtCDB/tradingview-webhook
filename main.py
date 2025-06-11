import os
import time
import hmac
import hashlib
import base64
import requests
import json

BASE_URL = "https://api.bitget.com"

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

def auth_headers(method, request_path, query_string="", body_str=""):
    ts = str(int(time.time() * 1000))
    prehash = ts + method.upper() + request_path
    if query_string:
        prehash += "?" + query_string
    prehash += body_str
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

def get_open_positions(product_type="USDT_FUTURES"):
    # Nota: endpoint correcto y query productType en mayúsculas y guion bajo
    request_path = "/api/v2/mix/position/all-position"
    query_string = f"productType={product_type}"
    headers = auth_headers("GET", request_path, query_string)
    url = BASE_URL + request_path + "?" + query_string
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return data.get("data") or []
    else:
        print(f"❌ Error listando posiciones: {r.status_code} - {r.text}")
        return None

def place_order(symbol, side, size, price=None, reduce_only=False, margin_coin="USDT"):
    request_path = "/api/v2/mix/order/place-order"
    body = {
        "symbol": symbol,
        "side": side,           # "open_long", "close_long", "open_short", "close_short"
        "size": size,
        "marginCoin": margin_coin,
        "reduceOnly": reduce_only,
        "orderType": "limit" if price else "market"
    }
    if price:
        body["price"] = price
    body_str = json.dumps(body)
    headers = auth_headers("POST", request_path, "", body_str)
    url = BASE_URL + request_path
    r = requests.post(url, headers=headers, data=body_str)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"❌ Error colocando orden: {r.status_code} - {r.text}")
        return None

# Ejemplo integración con señales (simplificado)
def handle_signal(signal, symbol, size):
    # Trae posiciones abiertas para validar estado
    posiciones = get_open_positions()
    # Aquí lógica ejemplo para EXIT_CONFIRMED
    if signal == "EXIT_CONFIRMED":
        # Si tienes posición LONG, cerrar long
        for pos in posiciones:
            if pos["symbol"] == symbol:
                if pos["holdSide"] == "long" and float(pos["total"]) > 0:
                    print(f"Cerrando LONG en {symbol}")
                    return place_order(symbol, "close_long", size, reduce_only=True)
                elif pos["holdSide"] == "short" and float(pos["total"]) > 0:
                    print(f"Cerrando SHORT en {symbol}")
                    return place_order(symbol, "close_short", size, reduce_only=True)
    # Otras señales y lógica aquí...

if __name__ == "__main__":
    # Ejemplo prueba
    symbol = "SOLUSDT"
    size = 1
    print("Posiciones abiertas:", get_open_positions())
    print(handle_signal("EXIT_CONFIRMED", symbol, size))
