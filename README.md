[README.md](https://github.com/user-attachments/files/21764197/README.md)
# Pocket Option Bot — Confluencia + Telegram + Estadísticas (Demo listo)

> **⚠️ Aviso**: El trading con opciones binarias es de ALTO RIESGO. Este bot es solo para fines educativos. Úsalo bajo tu propio riesgo.

## ¿Qué incluye?
- **Múltiples temporalidades**: 5s, 15s, 30s, 1m (agregadas a partir de ticks).
- **Confluencia de estrategias** con indicadores: RSI, MACD, Alligator, EMA 35/50.
- **Módulo de confianza**: filtra baja volatilidad, rango choppy, horarios débiles y pobre racha reciente.
- **Telegram**: envía señales y alertas a tu bot.
- **Estadísticas internas**: winrate, mejores horarios y mejores pares.
- **Modo DEMO**: si no tienes el WebSocket listo, corre `--demo` para ver el flujo completo.

## Estructura
```
pocket_option_bot/
│  main.py
│  config.example.yaml
│  requirements.txt
│  README.md
├─ core/
│  ├─ candles.py
│  ├─ indicators.py
│  ├─ strategies.py
│  ├─ confluence.py
│  ├─ confidence_module.py
│  ├─ stats.py
│  └─ telegram_bot.py
└─ integrations/
   ├─ websocket_client.py     # Integra con tu WebSocket real de Pocket Option
   └─ demo_feed.py            # Simulador de ticks para DEMO
```

## Instalación rápida
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edita config.yaml con tu TOKEN y CHAT_ID de Telegram, y tus cookies si usas el WebSocket real.
python main.py --demo
```

## Uso con WebSocket real
- Reemplaza `integrations/websocket_client.py` con **tu versión final** (la que ya tienes que incluye cookies y filtro de payout 90–92%).  
- El bot usa la clase `PocketOptionStream` con:
  - `async def pairs(self) -> list[str]`
  - `async def ticks(self) -> AsyncIterator[dict]]` donde cada dict = `{ "pair": "EUR/USD", "bid": float, "ask": float, "ts": int }`
  - (Opcional) `def payout(self, pair) -> int`
- Lanza:
```bash
python main.py
```

## Señales
- El motor emite señales **CALL/PUT** a 1 minuto por defecto (configurable), cuando la **confluencia >= umbral** y el **módulo de confianza** permite operar.
- Se envía a Telegram y se registra en `data/signals.csv` y `data/stats.json`.

## Configuración
- Edita `config.yaml`:
  - `telegram.token` y `telegram.chat_id`
  - `engine.confluence_threshold` (0–100)
  - `engine.lookback_candles`
  - `risk.min_payout`: 90, 91 o 92
  - `risk.max_spread`: 0.0006, por ejemplo
  - `filters.allowed_sessions`: sesiones horarias permitidas

## Registrar resultados reales
- Cuando termine cada operación, puedes registrar **WIN/LOSS** con un POST sencillo al endpoint local o añadiendo manualmente en `data/results.csv` (ver `stats.py`).

Suerte y buenos trades ✨
