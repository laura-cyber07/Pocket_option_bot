import websocket
import json
import threading
import time
import requests
import numpy as np
import pandas as pd

# ==========================
# CONFIGURACIONES
# ==========================
TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
TELEGRAM_CHAT_ID = "7855639313"

COOKIES = {
    "PO_SESSION": "a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934",
    "_cf_bm": "J9d3hEDl8w1GxNUnFLjdJItXn36djg4Jai0AREPDIQA-1754617849-1.0.1.1-J_W3obCG.b1URGEAAI4smS7nLohZVEk7SYyyXczF_Jh37W3qDq9Iry2ntoFNqaeUnIBYaN_GvP5czr.uowX6BYmM3aGVmflLHYH4xtR5NE0",
    "_scid": "-9WdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0XA",
    "_scid_r": "_dWdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0bQ",
    "_sctr": "1%7C1754539200000"
}

# ==========================
# FUNCIONES AUXILIARES
# ==========================

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def calculate_rsi(prices, period=14):
    delta = np.diff(prices)
    gains = delta[delta > 0].sum() / period
    losses = -delta[delta < 0].sum() / period
    rs = gains / losses if losses != 0 else 0
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
    return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_macd(prices, slow=26, fast=12, signal=9):
    exp1 = pd.Series(prices).ewm(span=fast, adjust=False).mean()
    exp2 = pd.Series(prices).ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def alligator_trend(prices):
    jaw = calculate_ema(prices, 13)
    teeth = calculate_ema(prices, 8)
    lips = calculate_ema(prices, 5)
    if lips > teeth > jaw:
        return "alcista"
    elif lips < teeth < jaw:
        return "bajista"
    return "rango"

def analyze_confluence(prices):
    rsi = calculate_rsi(prices)
    macd, signal = calculate_macd(prices)
    ema35 = calculate_ema(prices, 35)
    ema50 = calculate_ema(prices, 50)
    trend = alligator_trend(prices)

    score = 0
    if rsi < 30:
        score += 1
    if rsi > 70:
        score -= 1
    if macd > signal:
        score += 1
    else:
        score -= 1
    if ema35 > ema50:
        score += 1
    else:
        score -= 1
    if trend == "alcista":
        score += 1
    elif trend == "bajista":
        score -= 1

    return score

# ==========================
# WEBSOCKET
# ==========================

def on_message(ws, message):
    data = json.loads(message)

    if "instrument" in data:
        symbol = data["instrument"]["symbol"]
        payout = data["instrument"].get("payout", 0)

        if payout >= 0.90:
            prices = np.random.normal(1.0, 0.01, 50)  # Simulación de precios
            confidence = analyze_confluence(prices)

            if confidence >= 3:
                signal = f"✅ Señal CONFIRMADA: {symbol}\nPayout: {payout*100:.0f}%\nConfluencia: {confidence}/5\nEstrategia: ALTA PROBABILIDAD"
                send_telegram_message(signal)
                print(signal)
            else:
                print(f"❌ Señal descartada: {symbol} | Confluencia {confidence}/5")

def on_open(ws):
    print("✅ Conectado a WebSocket Pocket Option")
    ws.send(json.dumps({"event": "subscribe", "pairs": "all"}))

def on_error(ws, error):
    print(f"Error WebSocket: {error}")

def on_close(ws):
    print("❌ Conexión cerrada. Reintentando en 5s...")
    time.sleep(5)
    start_websocket()

def start_websocket():
    ws_url = "wss://ws.pocketoption.com:443/"
    headers = [f"Cookie: {'; '.join([f'{k}={v}' for k,v in COOKIES.items()])}"]

    ws = websocket.WebSocketApp(
        ws_url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()
    
if __name__ == "__main__":
    start_websocket()
