#!/usr/bin/env python3
"""
pasar.py — monitor pasar kripto real-time via API publik Indodax.
Gratis, tanpa API key. Harga dalam Rupiah.

INI BUKAN MESIN PENCETAK UANG. Ini alat bantu: data harga live +
pantauan otomatis + peringatan. Keputusan dan risikonya tetap milikmu.

Pemakaian:
    python3 pasar.py harga btc
    python3 pasar.py daftar --limit 10
    python3 pasar.py ramai --limit 10        # pair paling ramai (vol IDR)
    python3 pasar.py cek btc --atas 1600000000 --bawah 140000000
    python3 pasar.py pantau btc --atas 1600000000 --bawah 140000000 --interval 60
"""
import json
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
API = "https://indodax.com/api"


def ambil_json(path, timeout=15):
    req = urllib.request.Request(API + path, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def normalisasi(simbol):
    s = simbol.strip().lower().replace("/", "_")
    if not s.endswith("_idr"):
        s = s + "_idr"
    return s


def rupiah(n):
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    if v >= 1000:
        return "Rp " + f"{v:,.0f}".replace(",", ".")
    if v == int(v):
        return "Rp " + str(int(v))
    return "Rp " + f"{v:,.2f}".replace(",", "x").replace(".", ",").replace("x", ".")


def cmd_harga(simbol):
    pair = normalisasi(simbol)
    try:
        t = ambil_json(f"/ticker/{pair.replace('_', '')}")["ticker"]
    except Exception as e:  # noqa: BLE001
        print(f"Gagal mengambil {pair}: {e}")
        sys.exit(2)
    print(f"{pair}: {rupiah(t['last'])}")
    print(f"  Beli: {rupiah(t['buy'])} | Jual: {rupiah(t['sell'])}")
    print(f"  Tertinggi: {rupiah(t['high'])} | Terendah: {rupiah(t['low'])}")
    print(f"  Vol: {t['vol_' + pair.split('_')[0]]} {pair.split('_')[0].upper()}")


def _semua_ticker():
    return ambil_json("/tickers")["tickers"]


def cmd_daftar(limit=10):
    ts = _semua_ticker()
    for i, (pair, t) in enumerate(sorted(ts.items()), 1):
        print(f"{pair:<14} {rupiah(t['last'])}")
        if i >= limit:
            break


def cmd_ramai(limit=10):
    ts = _semua_ticker()
    urut = sorted(ts.items(),
                  key=lambda kv: float(kv[1].get("vol_idr", 0)),
                  reverse=True)
    print(f"{'Pair':<14}{'Harga':<20}Volume IDR")
    for pair, t in urut[:limit]:
        print(f"{pair:<14}{rupiah(t['last']):<20}"
              f"{rupiah(t.get('vol_idr', 0))}")


def cek_level(simbol, atas=None, bawah=None):
    """Satu kali cek. Mengembalikan pesan peringatan atau ''."""
    pair = normalisasi(simbol)
    t = ambil_json(f"/ticker/{pair.replace('_', '')}")["ticker"]
    last = float(t["last"])
    pesan = []
    if atas and last >= atas:
        pesan.append(f"NAIK: {pair} menyentuh {rupiah(last)} "
                     f"(batas atas {rupiah(atas)})")
    if bawah and last <= bawah:
        pesan.append(f"TURUN: {pair} menyentuh {rupiah(last)} "
                     f"(batas bawah {rupiah(bawah)})")
    return t, pesan


def cmd_cek(simbol, atas=None, bawah=None):
    t, pesan = cek_level(simbol, atas, bawah)
    pair = normalisasi(simbol)
    if pesan:
        for p in pesan:
            print("ALERT: " + p)
    else:
        print(f"{pair}: {rupiah(t['last'])} — belum menyentuh batas.")


def cmd_pantau(simbol, atas=None, bawah=None, interval=60):
    pair = normalisasi(simbol)
    print(f"Memantau {pair} tiap {interval} dtk. Ctrl+C untuk berhenti.")
    try:
        while True:
            t, pesan = cek_level(simbol, atas, bawah)
            for p in pesan:
                print(f"[{time.strftime('%H:%M:%S')}] ALERT: {p}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nBerhenti memantau.")


def _angka(s):
    return float(s) if s else None


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    c = argv[1]
    # kumpulkan opsi --kunci nilai, dan argumen posisi (simbol)
    opt = {}
    posisi = []
    i = 2
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            posisi.append(argv[i])
            i += 1
    simbol = posisi[0] if posisi else ""
    try:
        if c == "harga" and simbol:
            cmd_harga(simbol)
        elif c == "daftar":
            cmd_daftar(int(opt.get("limit", 10)))
        elif c == "ramai":
            cmd_ramai(int(opt.get("limit", 10)))
        elif c == "cek" and simbol:
            cmd_cek(simbol, _angka(opt.get("atas")), _angka(opt.get("bawah")))
        elif c == "pantau" and simbol:
            cmd_pantau(simbol, _angka(opt.get("atas")), _angka(opt.get("bawah")),
                       int(opt.get("interval", 60)))
        else:
            print(__doc__)
    except Exception as e:  # noqa: BLE001
        print(f"Gagal: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
