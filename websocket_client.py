import websocket
import json
import threading
import requests
import time
from confidence_module import ConfidenceModule

# CONFIGURACIÓN
PO_COOKIES = {
    "PO_SESSION": "a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934",
    "_cf_bm": "J9d3hEDl8w1GxNUnFLjdJItXn36djg4Jai0AREPDIQA-1754617849-1.0.1.1-J_W3obCG.b1URGEAAI4smS7nLohZVEk7SYyyXczF_Jh37W3qDq9Iry2ntoFNqaeUnIBYaN_GvP5czr.uowX6BYmM3aGVmflLHYH4xtR5NE0",
    "_scid": "-9WdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0XA",
    "_scid_r": "_dWdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0bQ",
    "_sctr": "1%7C1754539200000"
}

TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
TELEGRAM_CHAT_ID = "7855639313"

# FILTRO DE PAYOUT
MIN_PAYOUT = 90
MAX_PAYOUT = 92

# Inicializar módulo de confianza
confidence = ConfidenceModule()

# Diccionario para almacenar velas
candles_data = {}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

def process_candle(pair, candle):
    if pair not in candles_data:
        candles_data[pair] = []
    candles_data[pair].append(candle)

    # Mantener solo últimas 50 velas
    if len(candles_data[pair]) > 50:
        candles_data[pair].pop(0)

    # Evaluar solo si tenemos suficientes velas
    if len(candles_data[pair]) >= 35:
        decision = confidence.evaluate(candles_data[pair])
        if decision != "NO_TRADE":
            send_telegram_message(f"📊 Señal {decision} en {pair} - Confianza alta ✅")

def on_message(ws, message):
    data = json.loads(message)

    # Filtro de activos y payout
    if data.get("type") == "asset_update":
        pair = data["symbol"]
        payout = data["payout"]

        if "OTC" in pair and MIN_PAYOUT <= payout <= MAX_PAYOUT:
            # suscribir a datos de velas
            ws.send(json.dumps({"command": "subscribe", "pair": pair, "interval": 60}))

    elif data.get("type") == "candle":
        pair = data["symbol"]
        candle = [
            data["timestamp"],  # time
            data["open"],       # open
            data["high"],       # high
            data["low"],        # low
            data["close"]       # close
        ]
        process_candle(pair, candle)

def on_error(ws, error):
    print(f"Error: {error}")
    send_telegram_message(f"❌ Error en WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Conexión cerrada")
    send_telegram_message("🔌 Conexión cerrada con Pocket Option")

def on_open(ws):
    print("Conectado a Pocket Option")
    send_telegram_message("✅ Bot conectado a Pocket Option y monitoreando activos OTC 90-92% payout")

if __name__ == "__main__":
    ws_url = "wss://api-msk.po.market/socket.io/?EIO=4&transport=websocket"
    headers = [f"Cookie: {'; '.join([f'{k}={v}' for k, v in PO_COOKIES.items()])}"]

    ws = websocket.WebSocketApp(ws_url,
                                header=headers,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open

    wst = threading.Thread(target=ws.run_forever)
    wst.start()

    # Mantener script vivo
    while True:
        time.sleep(1)
