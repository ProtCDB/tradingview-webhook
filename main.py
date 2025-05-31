from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    print("🔔 Alerta recibida de TradingView:")
    print(data)  # Esto mostrará en los logs el contenido del mensaje recibido
    return jsonify({'status': 'ok'})

@app.route('/', methods=['GET'])
def index():
    return "Servidor activo y esperando alertas."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
