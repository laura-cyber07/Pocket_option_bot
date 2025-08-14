
import requests

# Reemplaza con tu token y chat_id reales
TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
CHAT_ID = "7855639313"

def enviar_telegram(datos):
    if not datos or "mensaje" not in datos:
        return

    mensaje = datos["mensaje"]

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"⚠️ Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"❌ Excepción enviando a Telegram: {e}")
