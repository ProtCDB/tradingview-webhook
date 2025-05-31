from flask import Flask, request
import logging

app = Flask(__name__)

# Configurar logging para que muestre mensajes en los logs de Render
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()

    # Mostrar en logs qué mensaje fue recibido
    logging.info("📩 Alerta recibida: %s", data)

    return 'OK', 200

# Si alguien accede con GET, devuelve método no permitido (opcional pero recomendado)
@app.route('/', methods=['GET', 'HEAD', 'PUT', 'DELETE', 'PATCH'])
def method_not_allowed():
    return 'Método no permitido', 405
