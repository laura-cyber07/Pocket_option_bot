import asyncio
import json
import os
import websockets
import logging
import requests

# Configuración de logs
logging.basicConfig(level=logging.INFO)

# Variables desde Environment (Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PO_SESSION = os.getenv("PO_SESSION")
CF_BM = os.getenv("_CF_BM")
SCID = os.getenv("_SCID")
SCID_R = os.getenv("_SCID_R")
SCTR = os.getenv("_SCTR")

# Validación de variables
if not TELEGRAM_TOKEN or not CHAT_ID or not PO_SESSION:
    logging.error("Faltan variables en el entorno. Configura TELEGRAM_TOKEN, CHAT_ID y PO_SESSION.")
    exit(1)

# URL del WebSocket de Pocket Option
PO_WS_URL = "wss://ws.pocketoption.com/socket.io/?EIO=3&transport=websocket"

# Headers con cookies para autenticación
cookies = f"PO_SESSION={PO_SESSION}; _cf_bm={CF_BM}; _scid={SCID}; _scid_r={SCID_R}; _sctr={SCTR}"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": cookies
}

async def send_telegram_message(message):
    """Envía mensaje al bot de Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Error enviando mensaje a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Error en send_telegram_message: {e}")

async def handle_socket():
    """Conexión y manejo del WebSocket con Pocket Option"""
    try:
        async with websockets.connect(PO_WS_URL, extra_headers=headers, ping_interval=None) as ws:
            logging.info("✅ Conectado al WebSocket de Pocket Option")
            await send_telegram_message("✅ Bot conectado al WebSocket y funcionando 24/7")

            while True:
                msg = await ws.recv()
                if msg:
                    logging.info(f"Mensaje recibido: {msg}")

                    # Aquí puedes filtrar los datos de las señales
                    if "signal" in msg:
                        await send_telegram_message(f"📊 Señal detectada: {msg}")
    except Exception as e:
        logging.error(f"Error en handle_socket: {e}")
        await asyncio.sleep(5)
        logging.info("Reconectando...")
        await handle_socket()

if __name__ == "__main__":
    asyncio.run(handle_socket())
