#!/usr/bin/env python3
"""
data_xauusd.py — adaptor data XAUUSD untuk otak hplus agent.

Sumber gratis tanpa API key (terverifikasi 2026-10-01):
- Yahoo Finance v8: GC=F (COMEX gold futures, proksi spot XAUUSD),
  interval 5m/15m/30m/1h; H4 diagregasi dari H1.
- Yahoo Finance v8: DX-Y.NYB (US Dollar Index) harian untuk faktor DXY.

Hasil riset yang diimplementasikan di sini:
- Sesi (UTC): overlap London-NY 12:00-17:00 paling aktif; London 07:00-12:00;
  NY sore 17:00-21:45 momentum memudar; Asia 00:00-07:00 dead zone (chop);
  blackout rollover 21:45-23:15 UTC -> TIDAK ADA entry (sesi OFF_PEAK).
- Spread dimodelkan per sesi dalam POINT (1 pt = $0.01):
  Asia 20, London 35, overlap 45, NY sore 30, larut malam 25.
- DXY: korelasi invers ~-0.70 s/d -0.85 terhadap emas, TAPI bisa pecah
  saat risk-off ekstrem (emas & dolar naik bareng). Dipakai konfirmasi,
  bukan hukum.
- Emas spot tidak punya tape terpusat -> volume netral (price-only).
"""
import json
import urllib.request
from datetime import datetime, timezone

import indikator as ind
import news as modul_news
import teknikal as modul_teknikal

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart"
SIMBOL_EMAS = "GC=F"
SIMBOL_DXY = "DX-Y.NYB"


def ambil_yahoo(simbol, interval, range_="5d", timeout=25):
    url = f"{YAHOO}/{simbol}?interval={interval}&range={range_}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    data = {"open": [], "high": [], "low": [], "close": [], "vol": []}
    for o, h, l, c, v in zip(q["open"], q["high"], q["low"],
                             q["close"], q["volume"]):
        if None in (o, h, l, c):
            continue  # lewati bar rusak (gap akhir pekan)
        data["open"].append(float(o))
        data["high"].append(float(h))
        data["low"].append(float(l))
        data["close"].append(float(c))
        data["vol"].append(float(v or 0))
    return data


def agregat(kl, n):
    """Gabung tiap n candle jadi satu (dipakai untuk H4 dari H1)."""
    out = {"open": [], "high": [], "low": [], "close": [], "vol": []}
    for i in range(0, len(kl["close"]) - n + 1, n):
        s = slice(i, i + n)
        out["open"].append(kl["open"][s][0])
        out["high"].append(max(kl["high"][s]))
        out["low"].append(min(kl["low"][s]))
        out["close"].append(kl["close"][s][-1])
        out["vol"].append(sum(kl["vol"][s]))
    return out


def sesi_sekarang(waktu=None):
    """Kembalikan (nama_sesi, spread_point, boleh_entry).

    Aturan dari riset: blackout rollover 21:45-23:15 UTC -> entry dilarang.
    """
    w = waktu or datetime.now(timezone.utc)
    menit = w.hour * 60 + w.minute
    if 21 * 60 + 45 <= menit < 23 * 60 + 15:
        return "ROLLOVER_BLACKOUT", 150, False
    if menit < 7 * 60:
        return "ASIA", 20, True            # dead zone: chop
    if menit < 12 * 60:
        return "LONDON", 35, True
    if menit < 17 * 60:
        return "NY_OVERLAP", 45, True      # jendela utama
    if menit < 21 * 60 + 45:
        return "NY_SORE", 30, True         # momentum memudar
    return "LARUT", 25, True


def tren_dxy():
    """Tren DXY harian: UP = dolar menguat (headwind emas),
    DOWN = dolar melemah (tailwind emas)."""
    try:
        d = ambil_yahoo(SIMBOL_DXY, "1d", "6mo")
        tutup = d["close"]
        if len(tutup) < 60:
            return {"trend": "NEUTRAL", "nilai": 0.0}
        s20 = ind.sma(tutup, 20)
        s50 = ind.sma(tutup, 50)
        selisih = (s20 - s50) / s50
        if selisih > 0.002:
            tren = "UP"
        elif selisih < -0.002:
            tren = "DOWN"
        else:
            tren = "NEUTRAL"
        return {"trend": tren, "nilai": round(tutup[-1], 2)}
    except Exception:
        return {"trend": "NEUTRAL", "nilai": 0.0}


def bangun_processed_xauusd():
    tf = {
        "5m": ambil_yahoo(SIMBOL_EMAS, "5m", "5d"),
        "15m": ambil_yahoo(SIMBOL_EMAS, "15m", "1mo"),
        "30m": ambil_yahoo(SIMBOL_EMAS, "30m", "1mo"),
        "1h": ambil_yahoo(SIMBOL_EMAS, "1h", "3mo"),
    }
    tf["4h"] = agregat(tf["1h"], 4)

    m5, m15, m30, h1, h4 = (tf["5m"], tf["15m"], tf["30m"],
                            tf["1h"], tf["4h"])
    harga = m5["close"][-1]

    ma14 = ind.sma(m5["close"], 14)
    ma50 = ind.sma(m5["close"], 50)
    rsi_v = ind.rsi(m5["close"])
    macd_v, macd_sig = ind.macd(m5["close"])
    atr_v = ind.atr(m5["high"], m5["low"], m5["close"])
    if atr_v <= 0:
        atr_v = harga * 0.001

    chop = ind.choppiness(m5["high"], m5["low"], m5["close"])
    ker = ind.efficiency_ratio(m5["close"])

    arah_ut, _ = ind.ut_bot(h1["high"], h1["low"], h1["close"])
    ema200_h1 = ind.ema(h1["close"], min(200, len(h1["close"])))
    # Likuiditas: 2 bar H1 terbaru sering parsial (Yahoo lag) -> pakai
    # bar [-3] vs MEDIAN 24 bar sebelumnya (median tahan spike volume).
    _vv = sorted(h1["vol"][-27:-3]) if len(h1["vol"]) > 27 else [1]
    _med = _vv[len(_vv) // 2]
    low_liq = h1["vol"][-3] < _med * 0.4 if len(h1["vol"]) > 27 else False
    support, resistance = ind.support_resistance(h1["high"], h1["low"])

    ema50_h4 = ind.ema(h4["close"], 50)
    ema50_prev = ind.ema(h4["close"][:-10], 50)
    if harga > ema50_h4 and ema50_h4 >= ema50_prev:
        makro = "BULLISH"
    elif harga < ema50_h4 and ema50_h4 <= ema50_prev:
        makro = "BEARISH"
    else:
        makro = "SIDEWAYS"

    e1 = ind.ema(m30["close"], 20)
    e0 = ind.ema(m30["close"][:-10], 20)
    if e1 > e0 * 1.0005:
        arah_m30 = "BULLISH"
    elif e1 < e0 * 0.9995:
        arah_m30 = "BEARISH"
    else:
        arah_m30 = "SIDEWAYS"

    struktur_m15 = ind.struktur(m15["high"], m15["low"])
    mss_m5 = ind.mss(m5["high"], m5["low"], m5["close"])

    hi60 = max(h1["high"][-60:])
    lo60 = min(h1["low"][-60:])
    pos = (harga - lo60) / (hi60 - lo60) if hi60 > lo60 else 0.5
    zona = ("DISCOUNT" if pos < 0.33 else
            "PREMIUM" if pos > 0.66 else "EQUILIBRIUM")

    fvg = ind.fvg_status(m5["high"], m5["low"])
    lelah, bias, spike = ind.kelelahan(
        m5["high"], m5["low"], m5["close"], m5["vol"])

    vol_rata_m5 = (sum(m5["vol"][-21:-1]) / 20
                   if len(m5["vol"]) > 21 else 1)
    vol_vel = m5["vol"][-1] / vol_rata_m5 if vol_rata_m5 else 1.0

    nama_sesi, spread_pts, boleh_entry = sesi_sekarang()
    sesi_utc = "OFF_PEAK" if not boleh_entry else f"XAU_{nama_sesi}"
    # volume futures tidak sebanding dengan spot -> netralkan
    # (riset: spot XAUUSD tidak punya tape terpusat)

    try:
        info_news = modul_news.analisis(aset="XAUUSD")
    except Exception:
        info_news = {"bias": 0.0, "kekuatan": 0.0, "high_impact": False,
                     "jumlah": 0, "headlines": [], "bias_aset": 0.0,
                     "shock": {"aktif": False, "arah": 0, "judul": []}}
    # Fear & Greed adalah sentimen KRIPTO -> tidak relevan untuk emas.
    info_fund = {"fear_greed": {"nilai": 50, "klasifikasi": "n/a (emas)"},
                 "bias": 0.0, "tren_sentimen": "n/a (emas)"}
    try:
        info_tek = modul_teknikal.analisis(m5, h1)
    except Exception:
        info_tek = {"skor": 0.0, "kondisi": "?"}

    dxy = tren_dxy()

    return {
        "simbol": "XAUUSD",
        "market_info": {"spread": spread_pts, "symbol": "XAUUSD"},
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
            "volume_velocity": 1.0,   # dinetralkan: bukan volume spot
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
        "session_context_utc": {"current_trading_session": sesi_utc},
        "dxy": dxy,
        "sesi_emas": {"nama": nama_sesi, "spread_pts": spread_pts,
                      "boleh_entry": boleh_entry},
    }


if __name__ == "__main__":
    p = bangun_processed_xauusd()
    print(json.dumps({k: p[k] for k in
                      ("simbol", "dxy", "sesi_emas",
                       "session_context_utc")}, indent=2))
    print("harga:", p["m5_indicators"]["current_price"],
          "atr_m5:", round(p["m5_indicators"]["atr"], 2))
