
import websocket
import json
import time
import requests
from datetime import datetime

# ===== CONFIGURACIÓN DEL BOT =====
TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
TELEGRAM_CHAT_ID = "7855639313"

PO_COOKIES = {
    "PO_SESSION": "a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934",
    "_cf_bm": "J9d3hEDl8w1GxNUnFLjdJItXn36djg4Jai0AREPDIQA-1754617849-1.0.1.1-J_W3obCG.b1URGEAAI4smS7nLohZVEk7SYyyXczF_Jh37W3qDq9Iry2ntoFNqaeUnIBYaN_GvP5czr.uowX6BYmM3aGVmflLHYH4xtR5NE0",
    "_scid": "-9WdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0XA",
    "_scid_r": "_dWdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0bQ",
    "_sctr": "1%7C1754539200000",
    "cf_clearance": "35238566-cfe8-4311-a4d9-e65546c078e9-p"
}

MIN_PAYOUT = 85

# ===== FUNCIÓN PARA ENVIAR MENSAJE A TELEGRAM =====
def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        requests.post(url, json=payload)
    except Exception as e:
        print("Error enviando mensaje a Telegram:", e)

# ===== LÓGICA DE FILTRO DE ACTIVOS =====
def activo_valido(data):
    try:
        payout = data.get("payout", 0) * 100
        return payout >= MIN_PAYOUT
    except:
        return False

# ===== EVENTOS DEL WEBSOCKET =====
def on_message(ws, message):
    try:
        data = json.loads(message)
        if "active" in data:
            activo = data["active"]
            payout = data.get("payout", 0) * 100
            tendencia = data.get("trend", "Desconocida")

            if activo_valido(data):
                mensaje = f"📊 Activo: {activo}\n💰 Payout: {payout}%\n📈 Tendencia: {tendencia}\n⏰ Hora: {datetime.now().strftime('%H:%M:%S')}"
                enviar_telegram(mensaje)
                print("Enviado:", mensaje)
    except Exception as e:
        print("Error procesando mensaje:", e)

def on_error(ws, error):
    print("Error WebSocket:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket cerrado")

def on_open(ws):
    print("Conexión WebSocket abierta")

# ===== CONEXIÓN AL WEBSOCKET =====
def iniciar_websocket():
    headers = [
        f"Cookie: " + "; ".join([f"{k}={v}" for k, v in PO_COOKIES.items()])
    ]

    ws = websocket.WebSocketApp(
        "wss://ws.pocketoption.com:443",
        header=headers,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()

if __name__ == "__main__":
    enviar_telegram("🤖 Bot iniciado. Filtrando activos con payout >= 85%...")
    iniciar_websocket()
