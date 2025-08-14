#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_trading_bot.py (actualizado)
- WebSocket: wss://api-c.po.market/socket.io/?EIO=4&transport=websocket
- Reconexión automática y aviso por Telegram al reconectar (divertido)
- Incluye cookies y token del usuario (mantener privado)
- Interacción Telegram: elegir activo + temporalidad -> devuelve CALL/PUT/NO OPERAR
- Filtra activos con payout >= 85% y detecta tendencia clara
"""
import json, time, threading, ssl, traceback, os
from datetime import datetime
import requests

try:
    import websocket
except Exception:
    raise SystemExit("Instala dependencias: pip install websocket-client requests")

# ---------------- USER CONFIG ----------------
TELEGRAM_TOKEN = "8014109881:AAGuKq3yrxbMZbmD431Rx46whFTSNRBKmn8"
ALLOWED_CHAT_ID = "7855639313"

COOKIES = {
    "PO_SESSION": "a%3A4%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22a10f8aaad48ec7645b13694dedc1b7d2%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A13%3A%22108.21.71.211%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A111%3A%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1754539037%3B%7D904ef2647178a06bab08deb565568934",
    "_cf_bm": "J9d3hEDl8w1GxNUnFLjdJItXn36djg4Jai0AREPDIQA-1754617849-1.0.1.1-J_W3obCG.b1URGEAAI4smS7nLohZVEk7SYyyXczF_Jh37W3qDq9Iry2ntoFNqaeUnIBYaN_GvP5czr.uowX6BYmM3aGVmflLHYH4xtR5NE0",
    "_scid": "-9WdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0XA",
    "_scid_r": "_dWdoehCsNW8s08Ix0onH_JqWS81zMPZgjI0bQ",
    "_sctr": "1%7C1754539200000",
    "cf_clearance": "35238566-cfe8-4311-a4d9-e65546c078e9-p"
}

PAYOUT_MIN = 85  # mínimo payout aceptable
WS_URL = "wss://api-c.po.market/socket.io/?EIO=4&transport=websocket"
HOST_HEADER = "api-c.po.market"

LOG_FILE = "connection.log"
STATS_FILE = "stats.json"

TIMEFRAMES = ["5s","15s","30s","1m"]
CONFIDENCE_THRESHOLD = 90

CANDLE_CACHE = {}
ASSET_PAYOUTS = {}
ASSETS_IN_TREND = {}
CHAT_STATE = {}
STATS = {"sent":0,"accepted":0,"discarded":0,"history":[]}

# --------- utilidad ---------
def now_ts():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    line = f"[{now_ts()}] {msg}"
    print(line)
    try:
        with open(LOG_FILE,"a",encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        log("Telegram send error: " + str(e))

# --------- indicadores (simplificados) ---------
def ema(series, period):
    if not series: return []
    res=[]; k=2.0/(period+1)
    for i,v in enumerate(series):
        if i==0: res.append(v)
        else: res.append(v*k + res[-1]*(1-k))
    return res

def rsi(series, period=14):
    if len(series) < period+1: return None
    deltas=[series[i+1]-series[i] for i in range(len(series)-1)]
    gains=[d if d>0 else 0 for d in deltas]
    losses=[-d if d<0 else 0 for d in deltas]
    avg_gain=sum(gains[:period])/period
    avg_loss=sum(losses[:period])/period
    for i in range(period, len(gains)):
        avg_gain=(avg_gain*(period-1)+gains[i])/period
        avg_loss=(avg_loss*(period-1)+losses[i])/period
    rs = avg_gain / avg_loss if avg_loss!=0 else float('inf')
    return 100-100/(1+rs)

def macd(series, fast=12, slow=26, signal=9):
    if len(series) < slow: return None, None, None
    ef=ema(series, fast); es=ema(series, slow)
    if len(ef) > len(es): ef = ef[-len(es):]
    macd_line=[a-b for a,b in zip(ef,es)]
    signal_line=ema(macd_line, signal) if len(macd_line)>=signal else [0]*len(macd_line)
    hist = macd_line[-1] - signal_line[-1] if signal_line else 0
    return macd_line[-1], signal_line[-1] if signal_line else None, hist

def alligator_check(series):
    jaw=ema(series,13); teeth=ema(series,8); lips=ema(series,5)
    if not (jaw and teeth and lips): return None
    j=jaw[-1]; t=teeth[-1]; l=lips[-1]
    if l>t>j: return "up"
    if l<t<j: return "down"
    return "range"

def evaluate_confidence_and_direction(candles):
    closes=[c['close'] for c in candles]
    if len(closes) < 50: return 0, "NO_OP", []
    score=0; total=0; reasons=[]
    r = rsi(closes)
    if r is not None:
        total+=1
        if r<=30: score+=1; reasons.append("RSI oversold")
        elif r>=70: score+=1; reasons.append("RSI overbought")
    mv, ms, mh = macd(closes)
    if mv is not None:
        total+=1
        if mv>ms and mh>0: score+=1; reasons.append("MACD bullish")
        elif mv<ms and mh<0: score+=1; reasons.append("MACD bearish")
    a = alligator_check(closes)
    if a:
        total+=1
        if a in ("up","down"):
            score+=1; reasons.append("Alligator trend")
    ema35 = ema(closes,35)[-1] if len(closes)>=35 else None
    ema50 = ema(closes,50)[-1] if len(closes)>=50 else None
    if ema35 and ema50:
        total+=1
        if ema35>ema50 and closes[-1]>ema35: score+=1; reasons.append("EMA35>EMA50")
        elif ema35<ema50 and closes[-1]<ema35: score+=1; reasons.append("EMA35<EMA50")
    greens = sum(1 for i in range(1, 5) if last5[i] > last5[i-1])
    # parity simplified
    total+=1
    if closes[-1] > closes[-2]: score+=0.5; reasons.append("Last candle up")
    else: reasons.append("Last candle down")
    total+=1
    if len(closes)>=2 and ((closes[-2]<closes[-3] and closes[-1]>closes[-2]) or (closes[-2]>closes[-3] and closes[-1]<closes[-2])):
        score+=1; reasons.append("Pattern 1x1")
    confidence = int((score/max(1,total))*100)
    direction="NO_OP"
    if ema35 and ema50 and mv is not None:
        if ema35>ema50 and mv>ms: direction="CALL"
        elif ema35<ema50 and mv<ms: direction="PUT"
    if direction=="NO_OP":
        direction = "CALL" if closes[-1]>closes[-2] else "PUT"
    return confidence, direction, reasons

# --------- WebSocket message processing ---------
def extract_json(msg):
    try:
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8','ignore')
        if "{" in msg:
            payload = msg[msg.index("{"):]
            return json.loads(payload)
    except Exception:
        try:
            start=msg.index("{"); end=msg.rfind("}")+1
            return json.loads(msg[start:end])
        except: return None
    return None

def process_payload(payload):
    try:
        if not isinstance(payload, dict): return
        asset = payload.get("asset") or payload.get("symbol") or payload.get("pair")
        payout = None
        for k in ("payout","payoutPercent","profit"):
            if k in payload:
                try: payout = int(float(payload[k])); break
                except: payout=None
        candles = payload.get("candles") or payload.get("history") or payload.get("ohlc")
        if asset and payout:
            key = str(asset).replace(" ","").upper()
            ASSET_PAYOUTS[key]=payout
        if asset and isinstance(candles, list) and candles:
            standardized=[]
            for c in candles:
                if isinstance(c,list) and len(c)>=5:
                    t,o,h,l,cl = c[0],c[1],c[2],c[3],c[4]
                    standardized.append({"time":t,"open":float(o),"high":float(h),"low":float(l),"close":float(cl)})
                elif isinstance(c,dict) and all(k in c for k in ("open","close","high","low")):
                    standardized.append({"time":c.get("time"),"open":float(c.get("open")),"high":float(c.get("high")),"low":float(c.get("low")),"close":float(c.get("close"))})
            if standardized:
                key=str(asset).replace(" ","").upper()
                existing=CANDLE_CACHE.get(key,[])
                for s in standardized:
                    if not existing or existing[-1].get("time")!=s.get("time"):
                        existing.append(s)
                CANDLE_CACHE[key]=existing[-200:]
                # mark trend candidates
                payout_val = ASSET_PAYOUTS.get(key,0)
                if payout_val>=PAYOUT_MIN:
                    sc=CANDLE_CACHE[key]
                    if len(sc)>=60:
                        closes=[c['close'] for c in sc]
                        trend = alligator_check(closes)
                        ema35v = ema(closes,35)[-1] if len(closes)>=35 else None
                        ema50v = ema(closes,50)[-1] if len(closes)>=50 else None
                        if trend in ("up","down") and ema35v and ema50v:
                            ASSETS_IN_TREND[key]=payout_val
                        elif key in ASSETS_IN_TREND:
                            ASSETS_IN_TREND.pop(key,None)
                else:
                    ASSETS_IN_TREND.pop(key,None)
    except Exception as e:
        log("process_payload error: "+str(e))

# --------- WebSocket callbacks & reconnection ---------
def on_message(ws, message):
    payload = extract_json(message)
    if payload:
        process_payload(payload)

def on_error(ws, error):
    log("WS error: "+str(error))

def on_close(ws, code, msg):
    log(f"WebSocket closed: {code} {msg}")

def on_open(ws):
    log("WebSocket opened")

def ws_loop():
    headers = [
        f"Host: {HOST_HEADER}",
        "User-Agent: Mozilla/5.0",
        "Accept: */*",
        "Connection: keep-alive",
        "Cookie: " + "; ".join([f"{k}={v}" for k,v in COOKIES.items()])
    ]
    first_connect = True
    backoff = 1
    while True:
        try:
            log(f"Connecting to WS {WS_URL}")
            ws = websocket.WebSocketApp(WS_URL, header=headers, on_message=on_message, on_error=on_error, on_close=on_close)
            ws.on_open = on_open
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ws.run_forever(sslopt={"context":ctx, "ping_interval": 20, "ping_timeout": 10})
        except Exception as e:
            log("WS loop exception: "+str(e))
            log(traceback.format_exc())
        # reconnection backoff & notify
        time.sleep(backoff)
        if backoff < 60: backoff *= 2
        # send reconnect message to Telegram (fun)
        try:
            send_telegram(ALLOWED_CHAT_ID, "¡Volví, y vengo con todo 🚀 — reconectado al servidor!")
        except Exception: pass

# --------- Telegram handling (simple polling) ---------
LAST_UPDATE_ID = None
def list_assets_for_user():
    items = sorted(ASSETS_IN_TREND.items(), key=lambda x: x[1], reverse=True)
    if not items: return f"No hay activos en tendencia con payout >= {PAYOUT_MIN}% ahora."
    lines = [f"{k[:3]}/{k[3:6]} - payout {p}%" if len(k)>=6 else f"{k} - payout {p}%" for k,p in items]
    return "Activos (tendencia clara):\n" + "\n".join(lines)

def handle_updates_loop():
    global LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    backoff = 1
    while True:
        try:
            params = {"timeout":30}
            if LAST_UPDATE_ID: params["offset"] = LAST_UPDATE_ID + 1
            r = requests.get(url, params=params, timeout=40)
            data = r.json()
            if not data.get("ok"):
                time.sleep(backoff); continue
            for upd in data.get("result", []):
                LAST_UPDATE_ID = upd["update_id"]
                if "message" not in upd: continue
                msg = upd["message"]
                chat = msg.get("chat", {})
                chat_id = str(chat.get("id"))
                text = msg.get("text","").strip()
                log(f"Telegram message from {chat_id}: {text}")
                if ALLOWED_CHAT_ID and str(chat_id) != str(ALLOWED_CHAT_ID):
                    log("Ignoring chat "+chat_id); continue
                handle_user_message(chat_id, text)
            backoff = 1
        except Exception as e:
            log("Telegram loop error: "+str(e))
            time.sleep(backoff); backoff = min(60, backoff*2)

def handle_user_message(chat_id, text):
    lower = text.lower().strip()
    if lower in ("/start","start"):
        send_telegram(chat_id, "Hola — Bot AI Trading listo. Usa /assets para ver activos o envía 'EUR/USD 1m'.")
        return
    if lower in ("/assets","/activos"):
        send_telegram(chat_id, list_assets_for_user()); return
    if lower in ("/timeframes","/tf"):
        send_telegram(chat_id, "Temporalidades:\n- 5s\n- 15s\n- 30s\n- 1m"); return
    if lower in ("/stats","/estadisticas"):
        total = STATS.get("sent",0)
        accepted = STATS.get("accepted",0)
        discarded = STATS.get("discarded",0)
        pct = int(accepted/total*100) if total>0 else 0
        send_telegram(chat_id, f"Stats:\nTotal: {total}\nAprobadas: {accepted}\nDescartadas: {discarded}\nEfectividad aprox: {pct}%")
        return
    # expecting timeframe after sending asset
    state = CHAT_STATE.get(chat_id)
    if state and state.get("expect") == "tf":
        tf = text.strip()
        asset = state.get("asset")
        CHAT_STATE.pop(chat_id, None)
        analyze_for_user(chat_id, asset, tf)
        return
    parts = text.split()
    if len(parts) >= 2:
        tf = parts[-1]; asset = " ".join(parts[:-1])
        analyze_for_user(chat_id, asset, tf); return
    # if only asset provided, ask for timeframe
    possible_asset = text.strip()
    if possible_asset:
        CHAT_STATE[chat_id] = {"expect":"tf","asset":possible_asset}
        send_telegram(chat_id, f"Activo '{possible_asset}' recibido. Ahora envía la temporalidad (5s,15s,30s,1m).")
        return
    send_telegram(chat_id, "No entendí. Usa /assets o envía '<ACTIVO> <TEMPORALIDAD>' (ej: EUR/USD 1m).")

def analyze_for_user(chat_id, asset_input, timeframe):
    key = str(asset_input).replace(" ","").replace("/","").upper()
    candidate_key = None
    for k in list(CANDLE_CACHE.keys()):
        if key in k or k in key:
            candidate_key = k; break
    if not candidate_key:
        for k in ASSETS_IN_TREND.keys():
            if key in k or k in key:
                candidate_key = k; break
    if not candidate_key:
        send_telegram(chat_id, f"No tengo datos para '{asset_input}'. Espera a que el bot reciba historial o prueba otro activo.")
        return
    candles = CANDLE_CACHE.get(candidate_key, [])
    if not candles or len(candles) < 50:
        send_telegram(chat_id, f"No hay suficientes datos en cache para {asset_input}. Espera a que el WS reciba historial.")
        return
    sample = candles[-60:]
    confidence, direction, reasons = evaluate_confidence_and_direction(sample)
    if confidence >= CONFIDENCE_THRESHOLD:
        msg = f"✅ Señal: {candidate_key} {timeframe} → {direction}\\nConfiabilidad: {confidence}%"
        send_telegram(chat_id, msg)
        STATS["sent"] = STATS.get("sent",0) + 1
        STATS["accepted"] = STATS.get("accepted",0) + 1
        STATS["history"].append({"time": now_ts(), "pair": candidate_key, "tf": timeframe, "direction": direction, "confidence": confidence, "accepted": True})
    else:
        msg = f"⚠ No operar: {candidate_key} {timeframe} → {direction if 'direction' in locals() else 'N/A'}\\nConfiabilidad: {confidence}%"
        send_telegram(chat_id, msg)
        STATS["sent"] = STATS.get("sent",0) + 1
        STATS["discarded"] = STATS.get("discarded",0) + 1
        STATS["history"].append({"time": now_ts(), "pair": candidate_key, "tf": timeframe, "direction": direction if 'direction' in locals() else 'N/A', "confidence": confidence, "accepted": False})
    try: save_stats()
    except: pass
    send_telegram(chat_id, "¿Quieres otra operación? Responde 'sí' o 'no'.")

# ---- start ----
def start():
    t_ws = threading.Thread(target=ws_loop, daemon=True); t_ws.start()
    t_tg = threading.Thread(target=handle_updates_loop, daemon=True); t_tg.start()
    log("Bot started. Running WS and Telegram loops.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping bot...")

if __name__ == "__main__":
    start()
