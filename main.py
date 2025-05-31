import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Cargar claves desde variables de entorno
API_KEY = os.environ.get("BITGET_API_KEY")
API_SECRET = os.environ.get("BITGET_SECRET")
API_PASSPHRASE = os.environ.get("BITGET_PASSPHRASE")

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    signal = data.get("signal")

    if not signal:
        return jsonify({"error": "No signal provided"}), 400

    print(f"📩 Señal recibida: {signal}")

    if signal == "EXIT_CONFIRMED":
        # Aquí iría la lógica para cerrar la posición en Bitget
        print("🔐 Cerrando posición en Bitget... (simulado)")
        # TODO: Implementar con llamada real a la API
        return jsonify({"status": "exit confirmed received"}), 200

    return jsonify({"status": "signal received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
