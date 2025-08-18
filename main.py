import os
import threading
from flask import Flask
from websocket_client import start_websocket

# Crear la app Flask para el health check
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot funcionando correctamente en Render."

# Iniciar el servidor Flask en un hilo separado
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Iniciar el bot de Pocket Option
def run_bot():
    print("✅ Bot iniciado y conectado a Pocket Option...")
    start_websocket()  # Esta función debe estar definida en websocket_client.py

if __name__ == "__main__":
    # Iniciar Flask en un hilo (para health check)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Iniciar el bot en el hilo principal
    run_bot()
