#!/usr/bin/env python3
"""
fundamental.py — analisis fundamental kripto.

Sumber gratis tanpa API key:
  - Fear & Greed Index (api.alternative.me)
  - (Kalender ekonomi: tidak ada sumber gratis yang stabil saat diuji,
    jadi event makro ditangkap lewat berita high-impact di news.py)

Keluaran: bias fundamental -1..1 + data mentah.
"""
import urllib.request
import json

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def fear_greed():
    try:
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=7", headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
        data = d.get("data", [])
        if not data:
            raise ValueError("kosong")
        kini = data[0]
        return {"nilai": int(kini["value"]),
                "klasifikasi": kini["value_classification"],
                "riwayat": [int(x["value"]) for x in data]}
    except Exception:
        return {"nilai": 50, "klasifikasi": "Netral (fallback)",
                "riwayat": []}


def analisis():
    fg = fear_greed()
    # 0-100 -> -1..1 (0 = extreme fear, 100 = extreme greed)
    bias = round((fg["nilai"] - 50) / 50.0, 3)
    # tren sentimen: naik 7 hari = menguat
    riw = fg["riwayat"]
    tren = "datar"
    if len(riw) >= 2:
        if riw[0] > riw[-1] + 5:
            tren = "menguat"
        elif riw[0] < riw[-1] - 5:
            tren = "melemah"
    return {"fear_greed": fg, "bias": bias, "tren_sentimen": tren,
            "catatan": ("Ekstrem takut = pasar murah (kontrarian bullish); "
                        "ekstrem serakah = waspada koreksi.")}


if __name__ == "__main__":
    import json as j
    print(j.dumps(analisis(), indent=2, ensure_ascii=False))
