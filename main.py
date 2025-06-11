import os
import time
import hmac
import hashlib
import requests
import json

# Carga variables de entorno
API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

BASE_URL = "https://api.bitget.com"

def get_timestamp():
    return str(int(time.time() * 1000))

def sign(method, request_path, timestamp, body=""):
    message = timestamp + method.upper() + request_path + body
    mac = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return mac.hexdigest()

def headers(method, request_path, body=""):
    timestamp = get_timestamp()
    sign_val = sign(method, request_path, timestamp, body)
    return {
        "Content-Type": "application/json",
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign_val,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
    }

def get_open_positions():
    # Usamos el endpoint que ya funcionó para ti (v2 mix positions)
    request_path = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    url = BASE_URL + request_path
    method = "GET"
    h = headers(method, request_path)
    r = requests.get(url, headers=h)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            return data["data"]
        else:
            print("No hay posiciones abiertas.")
            return []
    else:
        print(f"Error listando posiciones: {r.status_code} - {r.text}")
        return []

def close_position(symbol, size):
    # Cerrar posición con market order de sentido contrario al holdSide
    # Primero buscamos la posición abierta para saber si es long o short
    posiciones = get_open_positions()
    pos = next((p for p in posiciones if p["symbol"].upper() == symbol.upper()), None)
    if not pos:
        print(f"No se encontró posición abierta para {symbol}")
        return {"error": "No position found"}

    hold_side = pos["holdSide"]  # "long" o "short"
    margin_coin = pos["marginCoin"]
    margin_mode = pos["marginMode"]

    # Para cerrar una posición long, hay que hacer orden short y viceversa
    side = "close_short" if hold_side == "long" else "close_long"

    # Body para el endpoint de orden de cierre
    body = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "size": str(size),
        "side": side,
        "type": "market",
        "reduceOnly": True,
        "marginMode": margin_mode
    }

    request_path = "/api/mix/v1/order/placeOrder"
    url = BASE_URL + request_path
    method = "POST"
    body_json = json.dumps(body)
    h = headers(method, request_path, body_json)

    r = requests.post(url, headers=h, data=body_json)
    if r.status_code == 200:
        resp = r.json()
        print(f"Orden cierre enviada: {resp}")
        return resp
    else:
        print(f"Error cerrando posición: {r.status_code} - {r.text}")
        return {"error": r.text}

def main():
    print("=== Listando posiciones abiertas ===")
    posiciones = get_open_positions()
    print(json.dumps(posiciones, indent=2))

    if not posiciones:
        print("No hay posiciones abiertas, nada que cerrar.")
        return

    # Para prueba, toma el primer símbolo de las posiciones abiertas
    symbol = posiciones[0]["symbol"]
    size = float(posiciones[0]["total"])  # cantidad de contratos o tamaño

    print(f"Intentando cerrar posición en {symbol} tamaño {size}")
    resultado = close_position(symbol, size)
    print("Resultado del cierre:", resultado)

if __name__ == "__main__":
    main()
