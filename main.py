from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    print("🔔 Alerta recibida de TradingView:")
    print(data)
    return 'OK', 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))  # Render asigna el puerto en esta variable
    app.run(host='0.0.0.0', port=port)
