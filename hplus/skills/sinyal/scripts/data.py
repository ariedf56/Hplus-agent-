#!/usr/bin/env python3
"""
data.py — mengambil candle Binance (data-api.binance.vision, gratis)
dan membangun dict `processed` sesuai skema yang dimakan otak
(local_ai_scanner.py).

JUJUR: sebagian blok dihitung penuh dari candle (trend, momentum,
struktur, regime, lokasi). Sebagian disederhanakan (FVG, kelelahan)
dan sebagian netral (CVD, order block detail, berita). Lihat SKILL.md.
"""
import json
import urllib.request

import indikator as ind
import news as modul_news
import fundamental as modul_fundamental
import teknikal as modul_teknikal

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
DASAR = "https://data-api.binance.vision"
BATAS = 200


def ambil_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def klines(simbol, interval):
    url = (f"{DASAR}/api/v3/klines?symbol={simbol}"
           f"&interval={interval}&limit={BATAS}")
    data = ambil_json(url)
    # [open_time, o, h, l, c, v, ...]
    return {
        "open": [float(k[1]) for k in data],
        "high": [float(k[2]) for k in data],
        "low": [float(k[3]) for k in data],
        "close": [float(k[4]) for k in data],
        "vol": [float(k[5]) for k in data],
    }


def spread_simbol(simbol):
    try:
        b = ambil_json(
            f"{DASAR}/api/v3/ticker/bookTicker?symbol={simbol}")
        return abs(float(b["askPrice"]) - float(b["bidPrice"]))
    except Exception:
        return 0.0


def normalisasi_simbol(s):
    s = s.strip().upper().replace("/", "").replace("-", "")
    if not s.endswith("USDT"):
        s = s + "USDT"
    return s


def bangun_processed(simbol_user="BTC"):
    simbol = normalisasi_simbol(simbol_user)
    tf = {i: klines(simbol, i) for i in ("4h", "1h", "30m", "15m", "5m")}

    m5, m15, m30, h1, h4 = tf["5m"], tf["15m"], tf["30m"], tf["1h"], tf["4h"]
    harga = m5["close"][-1]

    # ---- M5: indikator inti ----
    ma14 = ind.sma(m5["close"], 14)
    ma50 = ind.sma(m5["close"], 50)
    rsi_v = ind.rsi(m5["close"])
    macd_v, macd_sig = ind.macd(m5["close"])
    atr_v = ind.atr(m5["high"], m5["low"], m5["close"])
    if atr_v <= 0:
        atr_v = harga * 0.001

    # ---- regime (dari M5, selaras dengan eksekusi) ----
    chop = ind.choppiness(m5["high"], m5["low"], m5["close"])
    ker = ind.efficiency_ratio(m5["close"])

    # ---- H1: UT Bot + EMA200 + S/R ----
    arah_ut, _ = ind.ut_bot(h1["high"], h1["low"], h1["close"])
    ema200_h1 = ind.ema(h1["close"], min(200, len(h1["close"])))
    vol_rata = sum(h1["vol"][-21:-1]) / 20 if len(h1["vol"]) > 21 else 1
    low_liq = h1["vol"][-1] < vol_rata * 0.5
    support, resistance = ind.support_resistance(h1["high"], h1["low"])

    # ---- H4: makro ----
    ema50_h4 = ind.ema(h4["close"], 50)
    ema50_prev = ind.ema(h4["close"][:-10], 50)
    if harga > ema50_h4 and ema50_h4 >= ema50_prev:
        makro = "BULLISH"
    elif harga < ema50_h4 and ema50_h4 <= ema50_prev:
        makro = "BEARISH"
    else:
        makro = "SIDEWAYS"

    # ---- M30: arah slope EMA20 ----
    e1 = ind.ema(m30["close"], 20)
    e0 = ind.ema(m30["close"][:-10], 20)
    if e1 > e0 * 1.0005:
        arah_m30 = "BULLISH"
    elif e1 < e0 * 0.9995:
        arah_m30 = "BEARISH"
    else:
        arah_m30 = "SIDEWAYS"

    # ---- M15: struktur, M5: MSS ----
    struktur_m15 = ind.struktur(m15["high"], m15["low"])
    mss_m5 = ind.mss(m5["high"], m5["low"], m5["close"])

    # ---- likuiditas: zona discount/premium dari range H1 ----
    hi60 = max(h1["high"][-60:])
    lo60 = min(h1["low"][-60:])
    pos = (harga - lo60) / (hi60 - lo60) if hi60 > lo60 else 0.5
    zona = ("DISCOUNT" if pos < 0.33 else
            "PREMIUM" if pos > 0.66 else "EQUILIBRIUM")

    # ---- SMC sederhana: FVG ----
    fvg = ind.fvg_status(m5["high"], m5["low"])

    # ---- kelelahan sederhana ----
    lelah, bias, spike = ind.kelelahan(
        m5["high"], m5["low"], m5["close"], m5["vol"])

    # ---- mikro: volume velocity ----
    vol_rata_m5 = (sum(m5["vol"][-21:-1]) / 20
                   if len(m5["vol"]) > 21 else 1)
    vol_vel = m5["vol"][-1] / vol_rata_m5 if vol_rata_m5 else 1.0

    spread = spread_simbol(simbol)

    # --- intelijen berita, fundamental, teknikal dalam ---
    try:
        info_news = modul_news.analisis(aset=simbol)
    except Exception:
        info_news = {"bias": 0.0, "kekuatan": 0.0, "high_impact": False,
                     "jumlah": 0, "headlines": [], "bias_aset": 0.0,
                     "shock": {"aktif": False, "arah": 0, "judul": []}}
    try:
        info_fund = modul_fundamental.analisis()
    except Exception:
        info_fund = {"fear_greed": {"nilai": 50, "klasifikasi": "?"},
                     "bias": 0.0, "tren_sentimen": "?"}
    try:
        info_tek = modul_teknikal.analisis(m5, h1)
    except Exception:
        info_tek = {"skor": 0.0, "kondisi": "?"}

    return {
        "simbol": simbol,
        "market_info": {"spread": spread, "symbol": simbol},
        "market_regime": {
            "choppiness_index": chop,
            "efficiency_ratio_ker": ker,
            "regime_status": "AUTO",
        },
        "ut_bot_h1": {
            "direction": arah_ut,
            "above_ema200": harga > ema200_h1,
            "low_liq": low_liq,
        },
        "m5_structure_shift": {"m5_structure_shift": mss_m5},
        "m5_indicators": {
            "current_price": harga,
            "ma14": ma14,
            "ma50": ma50,
            "rsi": rsi_v,
            "macd": macd_v,
            "macd_signal": macd_sig,
            "atr": atr_v,
        },
        "h4_macro_trend": {"h4_trend_direction": makro},
        "m30_trendline": {"trend_direction": arah_m30},
        "m15_structure": {"market_structure": struktur_m15},
        "cvd_order_flow": {},
        "micro_structure": {
            "score": 0.0,
            "structure_shift_micro": "NONE",
            "volume_velocity": round(vol_vel, 2),
        },
        "smc_concepts": {
            "order_block_status": "NONE",
            "fvg_status": fvg,
        },
        "liquidity_erl_irl": {"discount_premium_zone": zona},
        "h1_snr": {"support": support, "resistance": resistance},
        "rbs_sbr_structure": {"rbs_sbr_status": "NONE"},
        "candle_exhaustion": {
            "exhaustion_detected": lelah,
            "pressure_bias": bias,
            "volume_spike": spike,
        },
        "news_intelligence": {
            "high_impact_news_alert": info_news["high_impact"],
            "news_bias": info_news["bias"],
            "news_bias_aset": info_news["bias_aset"],
            "news_strength": info_news["kekuatan"],
            "news_shock": info_news["shock"],
            "jumlah": info_news["jumlah"],
            "headlines": info_news["headlines"],
        },
        "fundamental": info_fund,
        "analisis_teknikal": info_tek,
        "session_context_utc": {"current_trading_session": "CRYPTO_24_7"},
    }


if __name__ == "__main__":
    import sys
    p = bangun_processed(sys.argv[1] if len(sys.argv) > 1 else "BTC")
    print(json.dumps(p, indent=2)[:2000])
