from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Configura logging para que aparezca en Render
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    logging.info("🔔 Alerta recibida de TradingView:")
    logging.info(data)  # Esto sí se mostrará en Render correctamente
    return jsonify({'status': 'ok'})

@app.route('/', methods=['GET'])
def index():
    return "Servidor activo y esperando alertas."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
