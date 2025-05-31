from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    print("✅ Webhook recibido:", data)
    return 'OK', 200

@app.route('/')
def index():
    return 'Servidor activo', 200
