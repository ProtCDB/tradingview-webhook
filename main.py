from flask import Flask, request
import logging
import os

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info("📩 Alerta recibida: %s", data)
    return 'OK', 200

@app.route('/', methods=['GET', 'HEAD', 'PUT', 'DELETE', 'PATCH'])
def method_not_allowed():
    return 'Método no permitido', 405

# Obtener el puerto que Render espera usar
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Si no está definida, usa 10000 por defecto
    app.run(host='0.0.0.0', port=port)
