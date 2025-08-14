
import asyncio
import websockets
import json
import requests

TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
CHAT_ID = "7855639313"

async def connect():
    url = "wss://ws.pocketoption.com/"
    async with websockets.connect(url, extra_headers={
        "Cookie": "PO_SESSION=a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934"
    }) as ws:
        print("Conectado al WebSocket de Pocket Option")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            # Filtrado básico de payout
            if "payout" in str(data) and any(str(p) in str(data) for p in ["90", "91", "92"]):
                send_telegram("Nueva oportunidad detectada: " + str(data))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

if __name__ == "__main__":
    asyncio.run(connect())
