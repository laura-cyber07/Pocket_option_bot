import talib
import numpy as np

class ConfidenceModule:
    def _init_(self, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9,
                 ema_fast=35, ema_slow=50):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow

    def calculate_confidence(self, closes):
        closes = np.array(closes, dtype=float)

        # RSI
        rsi = talib.RSI(closes, timeperiod=self.rsi_period)
        last_rsi = rsi[-1]

        # MACD
        macd, macd_signal, _ = talib.MACD(closes,
                                          fastperiod=self.macd_fast,
                                          slowperiod=self.macd_slow,
                                          signalperiod=self.macd_signal)
        last_macd = macd[-1]
        last_signal = macd_signal[-1]

        # EMAs
        ema_fast = talib.EMA(closes, timeperiod=self.ema_fast)
        ema_slow = talib.EMA(closes, timeperiod=self.ema_slow)
        last_ema_fast = ema_fast[-1]
        last_ema_slow = ema_slow[-1]

        # Señales individuales
        signals = []

        # RSI sobrecompra/sobreventa
        if last_rsi < 30:
            signals.append("BUY")
        elif last_rsi > 70:
            signals.append("SELL")

        # MACD cruce
        if last_macd > last_signal:
            signals.append("BUY")
        elif last_macd < last_signal:
            signals.append("SELL")

        # EMA cruce
        if last_ema_fast > last_ema_slow:
            signals.append("BUY")
        elif last_ema_fast < last_ema_slow:
            signals.append("SELL")

        # Calcular confianza
        if len(signals) == 0:
            return 0, None

        buy_count = signals.count("BUY")
        sell_count = signals.count("SELL")

        if buy_count > sell_count:
            direction = "BUY"
            confidence = buy_count / len(signals)
        else:
            direction = "SELL"
            confidence = sell_count / len(signals)

        confidence_score = round(confidence * 100, 2)
        return confidence_score, direction
