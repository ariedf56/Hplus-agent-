#!/usr/bin/env python3
"""
teknikal.py — bedah teknikal dalam: Bollinger, Stochastic, ADX,
Pivot Point, Fibonacci. Memberi "opini kedua" independen selain
keputusan otak, plus level-level kunci untuk entry.

Semua murni Python, tanpa dependensi.
"""
import indikator as ind


def bollinger(closes, periode=20, mult=2.0):
    mid = ind.sma(closes, periode)
    data = closes[-periode:]
    var = sum((c - mid) ** 2 for c in data) / periode
    sd = var ** 0.5
    up, lo = mid + mult * sd, mid - mult * sd
    pct_b = (closes[-1] - lo) / (up - lo) if up > lo else 0.5
    return {"mid": mid, "atas": up, "bawah": lo, "pct_b": round(pct_b, 3)}


def stochastic(highs, lows, closes, periode=14):
    if len(closes) < periode:
        return {"k": 50.0, "d": 50.0}
    hh = max(highs[-periode:])
    ll = min(lows[-periode:])
    k = 100 * (closes[-1] - ll) / (hh - ll) if hh > ll else 50.0
    # %D = SMA3 dari %K (aproksimasi dari 3 titik)
    ks = []
    for i in range(3):
        seg = slice(-periode - i or None, -i or None)
        h, l = max(highs[seg]), min(lows[seg])
        c = closes[-1 - i]
        ks.append(100 * (c - l) / (h - l) if h > l else 50.0)
    d = sum(ks) / 3
    return {"k": round(k, 1), "d": round(d, 1)}


def adx(highs, lows, closes, periode=14):
    n = len(closes)
    if n < periode * 2 + 1:
        return 0.0
    plus_dm, minus_dm, trs = [], [], []
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        plus_dm.append(up if up > dn and up > 0 else 0.0)
        minus_dm.append(dn if dn > up and dn > 0 else 0.0)
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    def wilder(s):
        a = sum(s[:periode]) / periode
        for v in s[periode:]:
            a = (a * (periode - 1) + v) / periode
        return a
    atr_v = wilder(trs)
    if atr_v == 0:
        return 0.0
    pdi = 100 * wilder(plus_dm) / atr_v
    mdi = 100 * wilder(minus_dm) / atr_v
    dx = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0.0
    # ADX butuh smoothing kedua; aproksimasi: pakai DX terakhir
    return round(dx, 1), {"pdi": round(pdi, 1), "mdi": round(mdi, 1)}


def pivot(h1):
    """Pivot harian dari 24 candle H1 terakhir."""
    h, l, c = max(h1["high"][-24:]), min(h1["low"][-24:]), h1["close"][-1]
    pp = (h + l + c) / 3
    return {"pp": pp, "r1": 2 * pp - l, "s1": 2 * pp - h,
            "r2": pp + (h - l), "s2": pp - (h - l)}


def fibonacci(highs, lows):
    sw = ind.swings(highs, lows)
    sh = [p for _, p, t in sw if t == "high"]
    sl = [p for _, p, t in sw if t == "low"]
    if not sh or not sl:
        return {}
    hi, lo = sh[-1], sl[-1]
    rentang = hi - lo
    if rentang <= 0:
        return {}
    return {str(k): round(hi - rentang * k, 2)
            for k in (0.236, 0.382, 0.5, 0.618, 0.786)}


def analisis(m5, h1):
    harga = m5["close"][-1]
    bb = bollinger(m5["close"])
    st = stochastic(m5["high"], m5["low"], m5["close"])
    adx_v, dmi = adx(m5["high"], m5["low"], m5["close"])
    pv = pivot(h1)
    fib = fibonacci(h1["high"], h1["low"])

    # --- skor komposit -1..1 (opini kedua) ---
    skor = 0.0
    # Bollinger %B: <0.2 oversold (bullish), >0.8 overbought (bearish)
    if bb["pct_b"] < 0.2:
        skor += 0.25
    elif bb["pct_b"] > 0.8:
        skor -= 0.25
    # Stochastic
    if st["k"] < 20 and st["d"] < 20:
        skor += 0.2
    elif st["k"] > 80 and st["d"] > 80:
        skor -= 0.2
    # ADX + DMI: tren kuat searah DMI dominan
    if adx_v > 25:
        skor += 0.3 if dmi["pdi"] > dmi["mdi"] else -0.3
    # Posisi vs pivot
    if harga > pv["r1"]:
        skor -= 0.15  # jauh di atas pivot: rawan jenuh
    elif harga < pv["s1"]:
        skor += 0.15
    # Fibonacci: dekat 0.618 dari bawah = area beli
    if fib:
        lv = fib.get("0.618", 0)
        atr_v = ind.atr(m5["high"], m5["low"], m5["close"]) or harga * 0.001
        if abs(harga - lv) < atr_v * 0.5 and harga > lv:
            skor += 0.1
    skor = round(max(-1.0, min(1.0, skor)), 3)

    kondisi = ("TREND_KUAT" if adx_v > 25 else
               "SIDEWAYS" if adx_v < 20 else "TRANSISI")
    return {"skor": skor, "kondisi": kondisi, "adx": adx_v,
            "bollinger": bb, "stochastic": st,
            "pivot": {k: round(v, 2) for k, v in pv.items()},
            "fibonacci": fib, "harga": harga}
