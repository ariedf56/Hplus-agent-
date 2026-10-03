#!/usr/bin/env python3
"""
indikator.py — pustaka indikator teknikal murni Python (tanpa numpy).

Dipakai untuk membangun data yang dimakan oleh otak
(local_ai_scanner.py). Semua fungsi menerima list float
(urutan lama -> baru) dan mengembalikan nilai terakhir.
"""
import math


def sma(values, period):
    if len(values) < period or period <= 0:
        return 0.0
    return sum(values[-period:]) / period


def ema(values, period):
    if len(values) < period or period <= 0:
        return 0.0
    k = 2.0 / (period + 1.0)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def ema_series(values, period):
    """Deret EMA penuh (untuk MACD)."""
    if len(values) < period or period <= 0:
        return [0.0] * len(values)
    k = 2.0 / (period + 1.0)
    out = [0.0] * len(values)
    e = sum(values[:period]) / period
    out[period - 1] = e
    for i in range(period, len(values)):
        e = values[i] * k + e * (1 - k)
        out[i] = e
    return out


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains) / period
    al = sum(losses) / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - 100.0 / (1 + rs)


def macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return 0.0, 0.0
    ef = ema_series(closes, fast)
    es = ema_series(closes, slow)
    line = [a - b for a, b in zip(ef, es)]
    sig = ema_series(line[slow - 1:], signal)
    return line[-1], sig[-1]


def atr(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1:
        return 0.0
    trs = []
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def choppiness(highs, lows, closes, period=14):
    """Choppiness Index 0-100. >61.8 choppy, <38.2 trending."""
    if len(closes) < period + 1:
        return 50.0
    a = atr(highs[-period - 1:], lows[-period - 1:],
            closes[-period - 1:], period)
    hi = max(highs[-period:])
    lo = min(lows[-period:])
    if hi - lo <= 0 or a <= 0:
        return 50.0
    return 100.0 * math.log10(a / (hi - lo)) / math.log10(period)


def efficiency_ratio(closes, period=14):
    """Kaufman Efficiency Ratio 0-1. >0.6 efisien/trending."""
    if len(closes) < period + 1:
        return 0.5
    perubahan = abs(closes[-1] - closes[-period - 1])
    volatilitas = sum(abs(closes[i] - closes[i - 1])
                      for i in range(len(closes) - period, len(closes)))
    if volatilitas == 0:
        return 0.5
    return min(perubahan / volatilitas, 1.0)


def ut_bot(highs, lows, closes, key=1.0, atr_period=10):
    """
    Aproksimasi 'UT Bot Alerts' (TradingView).
    Mengembalikan (direction, trailing_stop).
    direction: 'BULLISH' / 'BEARISH'
    """
    n = len(closes)
    if n < atr_period + 2:
        return "BULLISH", closes[-1] if closes else 0.0
    a = atr(highs, lows, closes, atr_period)
    nloss = key * a
    stop = 0.0
    pos = 0
    prev_stop = closes[0]
    for i in range(1, n):
        c = closes[i]
        pc = closes[i - 1]
        if c > prev_stop and pc > prev_stop:
            stop = max(prev_stop, c - nloss)
        elif c < prev_stop and pc < prev_stop:
            stop = min(prev_stop, c + nloss)
        elif c > prev_stop:
            stop = c - nloss
        else:
            stop = c + nloss
        if pc < prev_stop and c > prev_stop:
            pos = 1
        elif pc > prev_stop and c < prev_stop:
            pos = -1
        prev_stop = stop
    return ("BULLISH" if pos >= 0 else "BEARISH"), stop


def swings(highs, lows, kiri=2, kanan=2):
    """Fraktal swing. Mengembalikan [(index, harga, 'high'/'low')]."""
    out = []
    n = len(highs)
    for i in range(kiri, n - kanan):
        if all(highs[i] >= highs[i - j] for j in range(1, kiri + 1)) and \
           all(highs[i] >= highs[i + j] for j in range(1, kanan + 1)) and \
           (highs[i] > highs[i - 1] or highs[i] > highs[i + 1]):
            out.append((i, highs[i], "high"))
        if all(lows[i] <= lows[i - j] for j in range(1, kiri + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, kanan + 1)) and \
           (lows[i] < lows[i - 1] or lows[i] < lows[i + 1]):
            out.append((i, lows[i], "low"))
    return out


def struktur(highs, lows):
    """Struktur pasar dari swing: BULLISH/BEARISH/NEUTRAL."""
    sw = swings(highs, lows)
    sh = [p for _, p, t in sw if t == "high"][-2:]
    sl = [p for _, p, t in sw if t == "low"][-2:]
    if len(sh) == 2 and len(sl) == 2:
        if sh[1] > sh[0] and sl[1] > sl[0]:
            return "BULLISH"
        if sh[1] < sh[0] and sl[1] < sl[0]:
            return "BEARISH"
    return "NEUTRAL"


def mss(highs, lows, closes):
    """Market Structure Shift pada timeframe itu."""
    sw = swings(highs, lows)
    sh = [p for _, p, t in sw if t == "high"]
    sl = [p for _, p, t in sw if t == "low"]
    c = closes[-1]
    if sh and c > sh[-1]:
        return "BULLISH_MSS"
    if sl and c < sl[-1]:
        return "BEARISH_MSS"
    return "NONE"


def support_resistance(highs, lows):
    sw = swings(highs, lows)
    sh = [p for _, p, t in sw if t == "high"]
    sl = [p for _, p, t in sw if t == "low"]
    return (sl[-1] if sl else 0.0, sh[-1] if sh else 0.0)


def fvg_status(highs, lows, lihat=8):
    """Fair Value Gap sederhana dari candle terakhir."""
    n = len(highs)
    for i in range(n - 1, max(n - lihat - 1, 2), -1):
        if lows[i] > highs[i - 2]:
            return "BULLISH_FVG"
        if highs[i] < lows[i - 2]:
            return "BEARISH_FVG"
    return "NONE"


def kelelahan(highs, lows, closes, volumes, period=14):
    """
    Deteksi kelelahan sederhana: candle jumbo + volume spike.
    Mengembalikan (terdeteksi, bias, volume_spike).
    """
    a = atr(highs, lows, closes, period)
    if a <= 0 or len(volumes) < 21:
        return False, "NEUTRAL", False
    i = -1
    rentang = highs[i] - lows[i]
    vol_rata = sum(volumes[-21:-1]) / 20
    spike = volumes[i] > vol_rata * 1.5
    jumbo = rentang > a * 2.0
    naik = closes[i] > closes[i - 1]
    if jumbo and spike:
        return True, ("BUYING" if naik else "SELLING"), True
    return False, "NEUTRAL", spike
