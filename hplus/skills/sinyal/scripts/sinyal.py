#!/usr/bin/env python3
"""
sinyal.py — CLI skill sinyal: jalankan otak scanner di data live,
catat sinyal ke jurnal, dan (opsional) eksekusi PAPER TRADING.

PAPER TRADING = simulasi dengan uang mainan. Tidak ada order sungguhan,
tidak ada API exchange, tidak ada risiko finansial. Ini cara aman
memvalidasi cara berpikir scanner sebelum (atau tanpa) uang asli.

Pemakaian:
    python3 sinyal.py pindai BTC
    python3 sinyal.py pindai XAUUSD            # emas (adaptor khusus)
    python3 sinyal.py pindai BTC --json          # untuk cron
    python3 sinyal.py pindai BTC --paper         # + eksekusi paper otomatis
    python3 sinyal.py portofolio
    python3 sinyal.py jurnal --limit 10
"""
import datetime
import json
import os
import sys

import data as dt
import data_xauusd as dt_xau
from local_ai_scanner import (powerful_local_ai_scanner_v2,
                              powerful_local_ai_scanner_xau)

DASAR = os.path.dirname(os.path.abspath(__file__))
F_JURNAL = os.path.join(DASAR, "jurnal.json")
F_PORTO = os.path.join(DASAR, "portofolio.json")

SALDO_AWAL = 1000.0      # USDT mainan
RISIKO_PERSEN = 1.0      # risiko per posisi (% saldo)
MODAL_PERSEN = 10.0      # modal per posisi (% saldo)
SL_ATR = 1.5
TP_ATR = 3.0             # risk:reward 1:2
AMBANG_CONF = 0.58       # ambang confidence minimum (selaras otak)


def _muat(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _simpan(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def sekarang():
    return datetime.datetime.now().isoformat(timespec="seconds")


def rupiah_dolar(v):
    return f"${v:,.2f}"


# ---------------- paper trading ----------------

def porto_muat():
    return _muat(F_PORTO, {"saldo": SALDO_AWAL, "posisi": [],
                           "riwayat": []})


def porto_simpan(p):
    _simpan(F_PORTO, p)


def update_posisi(p, harga):
    """Cek SL/TP posisi terbuka pada harga kini. Kembalikan daftar tutup."""
    tutup = []
    sisa = []
    for pos in p["posisi"]:
        arah = 1 if pos["arah"] == "BUY" else -1
        kena_sl = (harga <= pos["sl"]) if arah == 1 else (harga >= pos["sl"])
        kena_tp = (harga >= pos["tp"]) if arah == 1 else (harga <= pos["tp"])
        if kena_sl or kena_tp:
            keluar = pos["sl"] if kena_sl else pos["tp"]
            pnl = (keluar - pos["masuk"]) / pos["masuk"] * pos["modal"] * arah
            p["saldo"] += pnl
            pos.update({"keluar": keluar, "pnl": round(pnl, 2),
                        "status": "TP" if kena_tp else "SL",
                        "waktu_tutup": sekarang()})
            p["riwayat"].append(pos)
            tutup.append(pos)
        else:
            pos["harga_kini"] = harga
            pnl_jalan = ((harga - pos["masuk"]) / pos["masuk"]
                         * pos["modal"] * arah)
            pos["pnl_jalan"] = round(pnl_jalan, 2)
            sisa.append(pos)
    p["posisi"] = sisa
    return tutup


def buka_posisi(p, simbol, aksi, harga, atr, confidence, pengali=1.0):
    for pos in p["posisi"]:
        if pos["simbol"] == simbol:
            return None  # sudah ada posisi di simbol ini
    modal = p["saldo"] * MODAL_PERSEN / 100.0 * pengali
    arah = 1 if aksi == "BUY" else -1
    sl = harga - arah * SL_ATR * atr
    tp = harga + arah * TP_ATR * atr
    pos = {"simbol": simbol, "arah": aksi, "masuk": harga,
           "sl": round(sl, 4), "tp": round(tp, 4),
           "modal": round(modal, 2), "atr": round(atr, 4),
           "confidence": confidence, "waktu_buka": sekarang()}
    p["posisi"].append(pos)
    return pos


# ---------------- perintah ----------------

def ringkas_hasil(hasil, simbol, harga, processed):
    d = hasil["decision"]
    garis = [
        f"Simbol   : {simbol}",
        f"Keputusan: {d['action']}  (confidence {d['confidence']:.2f})",
        f"Regime   : {hasil['regime'].get('name', '-')}",
        f"Harga    : {harga}",
        f"Alasan   : {d['reason']}",
    ]
    if d.get("target_price"):
        garis.append(f"Harga limit: {d['target_price']}")
    if d.get("risk_flags"):
        garis.append("Risk flags: " + ", ".join(d["risk_flags"]))
    ni = processed.get("news_intelligence", {}) or {}
    fund = processed.get("fundamental", {}) or {}
    tek = processed.get("analisis_teknikal", {}) or {}
    fg = fund.get("fear_greed", {}) or {}
    faktor_news = (hasil.get("factors", {}) or {}).get("news", {}) or {}
    shock = ni.get("news_shock", {}) or {}
    garis.append(
        f"Berita   : bias aset {ni.get('news_bias_aset', 0):+.2f} "
        f"| shock: {'YA' if shock.get('aktif') else 'tidak'} "
        f"({ni.get('jumlah', 0)} headline)")
    garis.append(
        f"Faktor NEWS di otak: skor {faktor_news.get('score', 0):+.2f} "
        f"(kualitas {faktor_news.get('quality', 0):.2f}) "
        f"<- {faktor_news.get('reason', '-')}")
    garis.append(
        f"Sentimen : Fear&Greed {fg.get('nilai', '?')} "
        f"({fg.get('klasifikasi', '?')})")
    garis.append(
        f"Teknikal : skor {tek.get('skor', 0):+.2f} "
        f"({tek.get('kondisi', '?')}, ADX {tek.get('adx', '?')})")
    for h in ni.get("headlines", [])[:3]:
        s = {1: "BULL", -1: "BEAR", 0: "NETRAL"}.get(h["sentimen"], "?")
        garis.append(f"  - [{s}] {h['judul'][:85]}")
    return "\n".join(garis)


def logika_lapisan(hasil, processed):
    """Lapisan baca-manusia di atas keputusan otak (v5).

    Berita kini dihitung DI DALAM otak sebagai faktor NEWS ke-11,
    jadi lapisan ini TIDAK memveto dan TIDAK mengubah confidence
    (menghindari hitung ganda). Tugasnya:
      1. Info regime berita/shock untuk ditampilkan di output & jurnal.
      2. Logika trading saat shock: volatilitas tinggi -> ukuran
         posisi paper dibagi 2 (position sizing adaptif).
      3. (Emas) sesi Asia = dead zone chop -> ukuran posisi paper
         dibagi 2 (riset 2026-10-01).
    Opini teknikal dalam tetap ditampilkan sebagai pembanding.
    """
    ni = processed.get("news_intelligence", {}) or {}
    shock = ni.get("news_shock", {}) or {}
    tek = processed.get("analisis_teknikal", {}) or {}
    pengali = 1.0
    flags = []
    catatan = []
    if shock.get("aktif"):
        pengali *= 0.5
        flags.append("NEWS_SHOCK")
    sesi = processed.get("sesi_emas", {}) or {}
    if sesi.get("nama") == "ASIA":
        pengali *= 0.5
        flags.append("ASIA_CHOP")
        catatan.append(
            "sesi Asia (dead zone): ukuran posisi paper dibagi 2")
    info = {"veto": None, "flags": flags, "catatan": catatan,
            "pengali_posisi": pengali,
            "shock": bool(shock.get("aktif"))}
    if shock.get("aktif"):
        arah = "bearish" if shock.get("arah") == -1 else "bullish"
        info["catatan"].append(
            f"shock {arah}: ukuran posisi paper dibagi 2")
        for j in (shock.get("judul") or [])[:2]:
            info["catatan"].append(f"shock: {j[:70]}")
    d = hasil["decision"]
    arah = 1 if d["action"] == "BUY" else (-1 if d["action"] == "SELL" else 0)
    skor_tek = tek.get("skor", 0.0) or 0.0
    if arah and abs(skor_tek) >= 0.5 and (skor_tek * arah) < 0:
        info["flags"].append("TEKNIKAL_KONFLIK")
        info["catatan"].append(
            f"opini teknikal {skor_tek:+.2f} melawan {d['action']} "
            f"(info saja, bukan veto)")
    return info


def cmd_pindai(simbol, sebagai_json=False, paper=False):
    # --- Emas: adaptor data + otak khusus (DXY, sesi, spread point) ---
    emas = simbol.strip().upper() in ("XAUUSD", "XAU", "GOLD", "EMAS")
    if emas:
        processed = dt_xau.bangun_processed_xauusd()
        hasil = powerful_local_ai_scanner_xau(processed)
    else:
        processed = dt.bangun_processed(simbol)
        hasil = powerful_local_ai_scanner_v2(processed)
    d = hasil["decision"]

    # --- lapisan logika news/fundamental/teknikal ---
    lapis = logika_lapisan(hasil, processed)
    if lapis["flags"]:
        d["risk_flags"] = d.get("risk_flags", []) + lapis["flags"]
    if lapis["veto"]:
        d["action"] = "HOLD"
        d["reason"] = d["reason"] + " | " + lapis["veto"]

    harga = processed["m5_indicators"]["current_price"]
    atr = processed["m5_indicators"]["atr"]
    sim = processed["simbol"]

    # jurnal: selalu catat
    j = _muat(F_JURNAL, [])
    j.append({"waktu": sekarang(), "simbol": sim,
              "aksi": d["action"], "confidence": d["confidence"],
              "harga": harga,
              "regime": hasil["regime"].get("name", "-"),
              "alasan": d["reason"]})
    _simpan(F_JURNAL, j[-500:])  # simpan 500 terakhir

    info_paper = []
    if paper:
        p = porto_muat()
        for t in update_posisi(p, harga):
            info_paper.append(
                f"Posisi {t['simbol']} {t['arah']} ditutup {t['status']}: "
                f"P/L {rupiah_dolar(t['pnl'])}")
        if d["action"] in ("BUY", "SELL") and d["confidence"] >= AMBANG_CONF:
            pos = buka_posisi(p, sim, d["action"], harga, atr,
                              d["confidence"],
                              pengali=lapis["pengali_posisi"])
            if pos:
                info_paper.append(
                    f"PAPER BUY/SELL dibuka: {sim} {d['action']} @ {harga} "
                    f"(SL {pos['sl']}, TP {pos['tp']})")
                if lapis["pengali_posisi"] < 1.0:
                    sebab = ", ".join(lapis["flags"]) or "risiko"
                    info_paper.append(
                        f"  -> ukuran posisi paper x{lapis['pengali_posisi']} "
                        f"({sebab})")
        porto_simpan(p)

    if sebagai_json:
        keluar = {"simbol": sim, "waktu": sekarang(),
                  "keputusan": d["action"],
                  "confidence": d["confidence"],
                  "harga": harga,
                  "regime": hasil["regime"].get("name"),
                  "alasan": d["reason"],
                  "lapisan": lapis,
                  "news": processed.get("news_intelligence"),
                  "fundamental": processed.get("fundamental"),
                  "teknikal": processed.get("analisis_teknikal"),
                  "paper": info_paper}
        print(json.dumps(keluar, ensure_ascii=False))
    else:
        print(ringkas_hasil(hasil, sim, harga, processed))
        for baris in info_paper:
            print(baris)


def cmd_portofolio():
    p = porto_muat()
    print(f"Saldo paper : {rupiah_dolar(p['saldo'])}")
    print(f"Posisi terbuka: {len(p['posisi'])}")
    for pos in p["posisi"]:
        print(f"  {pos['simbol']} {pos['arah']} @ {pos['masuk']} "
              f"| SL {pos['sl']} TP {pos['tp']} "
              f"| P/L jalan {rupiah_dolar(pos.get('pnl_jalan', 0))}")
    riw = p["riwayat"]
    if riw:
        total = sum(t["pnl"] for t in riw)
        menang = sum(1 for t in riw if t["pnl"] > 0)
        print(f"Riwayat: {len(riw)} trade, menang {menang}, "
              f"total P/L {rupiah_dolar(total)}")


def cmd_jurnal(limit=10):
    j = _muat(F_JURNAL, [])
    if not j:
        print("Jurnal kosong.")
        return
    for e in j[-limit:]:
        print(f"[{e['waktu']}] {e['simbol']} {e['aksi']} "
              f"(conf {e['confidence']:.2f}) @ {e['harga']}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    c = argv[1]
    if c == "pindai":
        simbol = argv[2] if len(argv) > 2 and not argv[2].startswith("--") else "BTC"
        cmd_pindai(simbol,
                   sebagai_json="--json" in argv,
                   paper="--paper" in argv)
    elif c == "portofolio":
        cmd_portofolio()
    elif c == "jurnal":
        limit = 10
        if "--limit" in argv:
            limit = int(argv[argv.index("--limit") + 1])
        cmd_jurnal(limit)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
