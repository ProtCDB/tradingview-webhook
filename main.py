import json
import requests
import time
import hmac
import hashlib

# Configuraciones base
BASE_URL = "https://api.bitget.com"
API_KEY = "TU_API_KEY"
API_SECRET = "TU_API_SECRET"
API_PASSPHRASE = "TU_PASSPHRASE"
PRODUCT_TYPE = "USDT-FUTURES"
MARGIN_COIN = "USDT"

# Función para generar headers autenticados
def auth_headers(method, endpoint, body=''):
    timestamp = str(int(time.time() * 1000))
    prehash = timestamp + method.upper() + endpoint + body
    signature = hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).hexdigest()

    return {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': API_PASSPHRASE,
        'Content-Type': 'application/json'
    }

# Obtener símbolo real
def get_real_symbol(symbol: str):
    try:
        endpoint = f"/api/v2/mix/market/contracts?productType={PRODUCT_TYPE}"
        headers = auth_headers("GET", endpoint)
        url = BASE_URL + endpoint
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            contracts = resp.json().get("data", [])
            for contract in contracts:
                if contract["symbol"].startswith(symbol.upper()):
                    return contract["symbol"]
        return None
    except Exception as e:
        print(f"❌ Error al obtener símbolo real: {e}")
        return None

# Listar posiciones
def list_positions(symbol: str):
    try:
        print(f"📨 Payload recibido: {{'signal': 'LIST_POSITIONS', 'symbol': '{symbol}'}}")

        if symbol != "ALL":
            real_symbol = get_real_symbol(symbol)
            if not real_symbol:
                print(f"❌ No se pudo encontrar un símbolo válido para {symbol}")
                return None

            print(f"✅ Símbolo real encontrado: {real_symbol}")
            endpoint = f"/api/mix/v1/position/singlePosition?symbol={real_symbol}&marginCoin={MARGIN_COIN}"
            headers = auth_headers("GET", endpoint)
            print(f"📡 Llamando a endpoint: {endpoint}")
            resp = requests.get(BASE_URL + endpoint, headers=headers)
        else:
            endpoint = "/api/mix/v1/position/allPosition"
            body = {
                "productType": PRODUCT_TYPE
            }
            json_body = json.dumps(body)
            headers = auth_headers("POST", endpoint, json_body)
            print(f"📡 Llamando a endpoint: {endpoint}")
            resp = requests.post(BASE_URL + endpoint, headers=headers, data=json_body)

        if resp.status_code == 200:
            positions = resp.json().get("data", [])
            print(f"📋 Posiciones abiertas: {positions}")
            return positions
        else:
            print(f"❌ Error listando posiciones: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción al listar posiciones: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    list_positions("SOLUSDT")
    list_positions("ALL")
