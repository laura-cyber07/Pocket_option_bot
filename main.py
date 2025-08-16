import asyncio
import json
import websockets
import requests
import statistics
from datetime import datetime
import pandas as pd
import numpy as np
import logging
import time

# === CONFIGURACIONES DEL USUARIO ===
TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
CHAT_ID = "7855639313"

# Cookies para autenticación WebSocket Pocket Option
COOKIES = {
    "PO_SESSION": "a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934",
    "_cf_bm": "J9d3hEDl8w1GxNUnFLjdJItXn36djg4Jai0AREPDIQA-1754617849-1.0.1.1-J_W3obCG.b1URGEAAI4smS7nLohZVEk7SYyyXczF_Jh37W3qDq9Iry2ntoFNqaeUnIBYaN_GvP5czr.uowX6BYmM3aGVmflLHYH4xtR5NE0",
    "_scid": "-9WdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0XA",
    "_scid_r": "_dWdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0bQ",
    "_sctr": "1%7C1754539200000"
}

# URL WebSocket oficial de Pocket Option
WS_URL = "wss://ws.pocketoption.com/"

# === CONFIGURACIÓN DE LOGGER ===
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(_name_)

# === FUNCIONES DE TELEGRAM ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    retries = 3  # Intentos de reintento

    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Si la respuesta no es 200, lanzará una excepción
            logger.info(f"Mensaje enviado a Telegram: {message}")
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje a Telegram (Intento {attempt + 1}/{retries}): {e}")
            time.sleep(2)  # Espera antes de reintentar
    logger.error("No se pudo enviar el mensaje a Telegram después de varios intentos.")

# === INDICADORES TÉCNICOS ===
def calculate_rsi(data, period=14):
    deltas = np.diff(data)
    ups = deltas[deltas > 0].sum() / period
    downs = abs(deltas[deltas < 0].sum()) / period
    rs = ups / downs if downs != 0 else 0
    return 100 - (100 / (1 + rs))

def calculate_ema(data, period):
    return pd.Series(data).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_macd(data, short=12, long=26, signal=9):
    short_ema = pd.Series(data).ewm(span=short, adjust=False).mean()
    long_ema = pd.Series(data).ewm(span=long, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

# === LÓGICA DE SEÑALES ===
def generate_signal(data):
    rsi = calculate_rsi(data)
    ema35 = calculate_ema(data, 35)
    ema50 = calculate_ema(data, 50)
    macd, signal_line = calculate_macd(data)

    conditions = []
    if rsi < 30:
        conditions.append("Sobreventa (RSI < 30)")
    elif rsi > 70:
        conditions.append("Sobrecompra (RSI > 70)")

    if ema35 > ema50:
        conditions.append("EMA35 > EMA50 (Tendencia Alcista)")
    else:
        conditions.append("EMA35 < EMA50 (Tendencia Bajista)")

    if macd > signal_line:
        conditions.append("MACD por encima del Signal (Compra)")
    else:
        conditions.append("MACD por debajo del Signal (Venta)")

    score = len([c for c in conditions if "Compra" in c or "Alcista" in c])
    return score, conditions

# === CLIENTE WEBSOCKET ===
async def run_bot():
    send_telegram_message("✅ Bot iniciado y conectado a Pocket Option...")
    async with websockets.connect(WS_URL, extra_headers={"Cookie": "; ".join([f"{k}={v}" for k,v in COOKIES.items()])}) as ws:
        await ws.send(json.dumps({"command": "get_candles"}))  # Simulación inicial

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                # Filtro ejemplo: candlestick
                if "candles" in data:
                    prices = [float(c["close"]) for c in data["candles"]]
                    if len(prices) > 50:
                        score, conditions = generate_signal(prices[-50:])
                        if score >= 2:  # Señal con al menos 2 confirmaciones
                            message = f"📊 Señal Detectada\nScore: {score}\nCondiciones:\n" + "\n".join(conditions)
                            send_telegram_message(message)
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"Error en la conexión WebSocket: {e}")
                break  # Salir del loop si hay un error con WebSocket

            except json.JSONDecodeError as e:
                logger.warning(f"Error al decodificar JSON: {e}")
                continue  # Continuar recibiendo mensajes

            await asyncio.sleep(1)  # Añadimos un pequeño retraso para evitar sobrecargar el servidor

asyncio.run(run_bot())
