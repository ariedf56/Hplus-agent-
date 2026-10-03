#!/usr/bin/env python3
"""
news.py — agregator berita kripto + logika dampak (news intelligence).

Sumber: RSS CoinDesk & CoinTelegraph (gratis, tanpa API key).
Setiap headline dinilai:
  - sentimen  : bullish (+1) / bearish (-1) / netral (0)
  - dampak    : 3 = high impact, 2 = sedang, 1 = rendah
  - aset      : BTC / ETH / SOL / XRP / CRYPTO (umum)

Keluaran dipakai otak (high_impact_news_alert) dan lapisan logika
di sinyal.py (news bias memveto/menguatkan entry).
"""
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

SUMBER = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
]

# Sumber makro/umum: dipakai untuk sentimen emas (Fed, CPI, NFP, geopolitik).
# CoinDesk/CoinTelegraph hampir tidak meliput emas, jadi tanpa ini
# bias_aset XAUUSD akan selalu kosong.
SUMBER_MAKRO = [
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Investing", "https://www.investing.com/rss/news_25.rss"),
]

BULLISH = [
    "etf approval", "approves etf", "etf approved", "all-time high",
    "record high", "bullish", "rally", "rallies", "surge", "surges",
    "breakout", "adoption", "institutional", "blackrock",
    "buys bitcoin", "bought bitcoin", "bitcoin reserve",
    "upgrade successful", "partnership", "integrates",
]
BEARISH = [
    "hack", "hacked", "exploit", "exploited", "ban", "banned", "bans",
    "lawsuit", "sued", "sues", "sec ", "crash", "plunge", "plunges",
    "dump", "dumps", "fraud", "scam", "bankrupt", "collapse", "collapses",
    "crackdown", "seized", "outflows", "sell-off", "selloff",
]
HIGH_IMPACT = [
    "etf", "sec", "federal reserve", "fed ", "interest rate", "rate cut",
    "rate hike", "cpi", "inflation data", "ban", "hack", "exploit", "lawsuit",
    "all-time high", "crash", "blackrock", "michael saylor",
]
ASET = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth"],
    "SOL": ["solana", "sol"],
    "XRP": ["xrp", "ripple"],
    "XAU": ["gold", "xauusd", "xau", "bullion", "precious metal"],
}

# --- Kamus khusus emas (logika trading, bukan veto) ---
# Bullish emas: dovish Fed / dolar melemah / permintaan safe haven naik.
BULLISH_XAU = [
    "rate cut", "rate cuts", "dovish", "fed cut", "easing",
    "weak dollar", "dollar falls", "dollar weakens", "dollar slides",
    "yields fall", "yields drop", "safe haven", "safe-haven",
    "central bank buying", "central banks buy", "gold buying",
    "gold reserve", "record high", "all-time high", "gold rally",
    "gold surges", "geopolitical", "missile", "airstrike", "war ",
    "recession fear", "de-dollarization",
]
# Bearish emas: hawkish Fed / dolar menguat / risk-on.
BEARISH_XAU = [
    "rate hike", "rate hikes", "hawkish", "fed hike", "tightening",
    "strong dollar", "dollar rises", "dollar strengthens", "dollar jumps",
    "yields rise", "yields surge", "yields jump", "risk-on",
    "gold falls", "gold drops", "gold slides", "gold slumps",
    "gold tumbles", "profit-taking", "gold selloff", "gold sell-off",
]
# Rilis yang paling menggerakkan emas (riset 2026-10-01):
# FOMC > CPI > NFP > PCE > PPI.
HIGH_IMPACT_XAU = [
    "fomc", "federal reserve", "powell", "rate decision",
    "rate cut", "rate hike", "cpi", "inflation data",
    "nonfarm", "nfp", "payrolls", "jobs report",
    "pce", "ppi", "interest rate",
]
# Frasa yang mengandung kata emas tapi BUKAN tentang emas fisik.
BUKAN_XAU = ["digital gold"]

BATAS_JAM_BIAS = 24
BATAS_JAM_IMPACT = 12
BATAS_JAM_SHOCK = 2  # berita dampak-3 berumur <= ini = shock pasar


def ambil_rss(nama, url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def umur_jam(pub_date):
    try:
        dt = parsedate_to_datetime(pub_date.strip())
        return (time.time() - dt.timestamp()) / 3600.0
    except Exception:
        return 999.0


def cocok(t, kunci):
    """Cocokkan kata/frasa. Kata pendek pakai batas kata penuh
    supaya 'ban' tidak cocok dengan 'banks', 'sol' tidak dengan 'sold'."""
    k = kunci.strip()
    if " " in k:
        return k in t
    return re.search(r"\b" + re.escape(k) + r"\b", t) is not None


def nilai_headline(judul):
    t = " " + judul.lower() + " "
    aset = "CRYPTO"
    for kode, kunci in ASET.items():
        if any(cocok(t, k) for k in kunci):
            if kode == "XAU" and any(k in t for k in BUKAN_XAU):
                continue  # mis. "digital gold" = narasi bitcoin, bukan emas
            aset = kode
            break
    if aset == "XAU":
        bull = sum(1 for k in BULLISH_XAU if cocok(t, k))
        bear = sum(1 for k in BEARISH_XAU if cocok(t, k))
        dampak_keys = HIGH_IMPACT_XAU
    else:
        bull = sum(1 for k in BULLISH if cocok(t, k))
        bear = sum(1 for k in BEARISH if cocok(t, k))
        dampak_keys = HIGH_IMPACT
    sentimen = 1 if bull > bear else (-1 if bear > bull else 0)
    # Makro (FOMC/CPI/NFP/...) selalu dampak-3, untuk aset apa pun,
    # karena rilis makro menggerakkan emas DAN kripto.
    makro = any(cocok(t, k) for k in HIGH_IMPACT_XAU)
    dampak = (3 if (makro or any(cocok(t, k) for k in dampak_keys))
             else (2 if sentimen else 1))
    return sentimen, dampak, aset, makro


def kumpulkan():
    semua = []
    for nama, url in SUMBER + SUMBER_MAKRO:
        try:
            xml_data = ambil_rss(nama, url)
            root = ET.fromstring(xml_data)
            for item in root.iter("item"):
                judul = (item.findtext("title") or "").strip()
                if not judul:
                    continue
                umur = umur_jam(item.findtext("pubDate") or "")
                if umur > BATAS_JAM_BIAS:
                    continue
                sentimen, dampak, aset, makro = nilai_headline(judul)
                semua.append({
                    "judul": judul,
                    "sumber": nama,
                    "umur_jam": round(umur, 1),
                    "sentimen": sentimen,
                    "dampak": dampak,
                    "aset": aset,
                    "makro": makro,
                })
        except Exception:
            continue  # satu sumber mati -> lanjut ke lainnya
    # buang duplikat judul
    unik, terlihat = [], set()
    for h in sorted(semua, key=lambda x: x["umur_jam"]):
        kunci = h["judul"][:60].lower()
        if kunci not in terlihat:
            terlihat.add(kunci)
            unik.append(h)
    return unik


def bias_tertimbang(heads):
    """Rata-rata sentimen berbobot (bobot = dampak x kesegaran)."""
    total_bobot, skor = 0.0, 0.0
    for h in heads:
        bobot = h["dampak"] * max(0.25, 1 - h["umur_jam"] / BATAS_JAM_BIAS)
        total_bobot += bobot
        skor += h["sentimen"] * bobot
    if not total_bobot:
        return 0.0, 0.0
    return skor / total_bobot, min(total_bobot / 20.0, 1.0)


def analisis(headlines=None, aset=None):
    heads = headlines if headlines is not None else kumpulkan()
    if not heads:
        return {"bias": 0.0, "kekuatan": 0.0, "high_impact": False,
                "jumlah": 0, "headlines": [],
                "bias_aset": 0.0, "shock": {"aktif": False, "arah": 0,
                                            "judul": []}}
    bias, kekuatan = bias_tertimbang(heads)

    # --- bias per aset: headline ber-tag aset tsb bobot penuh,
    #     headline CRYPTO umum ikut setengah bobot ---
    #     PENGECUALIAN: untuk XAUUSD hanya headline XAU + headline MAKRO
    #     (FOMC/CPI/NFP/PCE/PPI/Fed) yang dihitung, karena headline
    #     kripto (mis. hack exchange) tidak relevan untuk emas,
    #     sedangkan rilis makro adalah penggerak utama emas.
    bias_aset = bias
    if aset:
        a = aset.upper().replace("USDT", "")
        if a in ("XAUUSD", "XAU"):
            relevan = [h for h in heads
                       if h["aset"] == "XAU" or h.get("makro")]
        else:
            relevan = [h for h in heads
                       if h["aset"] == a or h["aset"] == "CRYPTO"]
        if relevan:
            bias_aset, _ = bias_tertimbang(relevan)

    # --- shock: berita dampak-3 yang masih segar ---
    def _aset_cocok(h, aset):
        if not aset:
            return True
        a = aset.upper().replace("USDT", "")
        tag = {"XAUUSD": "XAU"}.get(a, a)
        if tag == "XAU":
            return h["aset"] == "XAU" or bool(h.get("makro"))
        return h["aset"] in (a, "CRYPTO")

    shock_judul = [h for h in heads
                   if h["dampak"] == 3 and h["umur_jam"] <= BATAS_JAM_SHOCK
                   and h["sentimen"] != 0
                   and _aset_cocok(h, aset)]
    arah_shock = 0
    if shock_judul:
        b, _ = bias_tertimbang(shock_judul)
        arah_shock = 1 if b > 0.15 else (-1 if b < -0.15 else 0)

    # high_impact: hanya dari headline yang relevan untuk aset tsb
    # (untuk XAUUSD, hack exchange kripto bukan high impact emas).
    if aset and aset.upper().replace("USDT", "") in ("XAUUSD", "XAU"):
        heads_relevan = [h for h in heads
                         if h["aset"] == "XAU" or h.get("makro")]
    else:
        heads_relevan = heads
    high_impact = any(h["dampak"] == 3 and h["umur_jam"] <= BATAS_JAM_IMPACT
                      for h in heads_relevan)
    berdampak = sorted([h for h in heads if h["dampak"] >= 2],
                       key=lambda x: (-x["dampak"], x["umur_jam"]))[:5]
    return {"bias": round(bias, 3),
            "kekuatan": round(kekuatan, 3),
            "high_impact": high_impact,
            "jumlah": len(heads),
            "headlines": berdampak,
            "bias_aset": round(bias_aset, 3),
            "shock": {"aktif": bool(shock_judul) and arah_shock != 0,
                      "arah": arah_shock,
                      "judul": [h["judul"] for h in shock_judul[:3]]}}


if __name__ == "__main__":
    import json, sys
    hasil = analisis(aset=sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"bias={hasil['bias']} bias_aset={hasil['bias_aset']} "
          f"kekuatan={hasil['kekuatan']} high_impact={hasil['high_impact']} "
          f"jumlah={hasil['jumlah']}")
    sh = hasil["shock"]
    print(f"shock: aktif={sh['aktif']} arah={sh['arah']}")
    for j in sh["judul"]:
        print(f"  ! {j[:90]}")
    for h in hasil["headlines"]:
        s = {1: "BULL", -1: "BEAR", 0: "NETRAL"}[h["sentimen"]]
        print(f"  [dampak {h['dampak']}] [{s}] [{h['aset']}] [{h['sumber']}] {h['judul'][:80]}")
