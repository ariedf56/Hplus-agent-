#!/usr/bin/env python3
"""
xau_supertrend.py — sinyal live untuk strategi C5 (pemenang walk-forward).

Strategi (faithful ke backtest):
  XAUUSD H4, SuperTrend(7, 3.0) + filter ADX(14) > 20.
  - Flip SuperTrend + ADX > 20  -> ambil arah baru (LONG/SHORT)
  - Flip SuperTrend + ADX <= 20 -> FLAT (tunggu, hindari chop)
  - Risiko 1% per trade, unit risiko = 3x ATR(10) H4 (biaya ECN ~10c/oz/sisi)

Parameter (7,3,ADX20) dipilih via walk-forward 2 tahun data emas
(5 jendela OOS, semuanya positif) — lihat LAPORAN-BACKTEST.md.

Data: Yahoo Finance v8 GC=F 1h (gratis, tanpa API key), agregasi ke H4.

Pakai:
  python3 xau_supertrend.py sinyal            # cek sinyal sekarang
  python3 xau_supertrend.py sinyal --paper    # + update posisi paper
  python3 xau_supertrend.py status            # posisi paper saat ini
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

DASAR = os.path.dirname(os.path.abspath(__file__))
F_STATE = os.path.join(DASAR, "posisi.json")
F_JURNAL = os.path.join(DASAR, "jurnal_strategi.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

SALDO_AWAL = 1000.0
RISIKO_PERSEN = 1.0
BIAYA_OZ_RT = 0.20  # USD/oz round-trip (ECN)


def ambil_yahoo_1h():
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
           "?interval=1h&range=60d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    res = d["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    out = {"ts": [], "open": [], "high": [], "low": [],
           "close": [], "vol": []}
    for t, o, h, l, c, v in zip(ts, q["open"], q["high"], q["low"],
                                q["close"], q["volume"]):
        if None in (o, h, l, c):
            continue
        out["ts"].append(t)
        out["open"].append(float(o)); out["high"].append(float(h))
        out["low"].append(float(l)); out["close"].append(float(c))
        out["vol"].append(float(v or 0))
    return out


def ke_h4(d):
    out = {"ts": [], "open": [], "high": [], "low": [], "close": []}
    cur = None
    bucket = None
    for i, t in enumerate(d["ts"]):
        b = (t // 14400) * 14400
        if b != bucket:
            if cur:
                out["ts"].append(bucket); out["open"].append(cur[0])
                out["high"].append(cur[1]); out["low"].append(cur[2])
                out["close"].append(cur[3])
            bucket = b
            cur = [d["open"][i], d["high"][i], d["low"][i], d["close"][i]]
        else:
            cur[1] = max(cur[1], d["high"][i])
            cur[2] = min(cur[2], d["low"][i])
            cur[3] = d["close"][i]
    if cur:
        out["ts"].append(bucket); out["open"].append(cur[0])
        out["high"].append(cur[1]); out["low"].append(cur[2])
        out["close"].append(cur[3])
    return out


def atr_wilder(h, l, c, n=10):
    trs = [h[0] - l[0]]
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]),
                       abs(l[i] - c[i - 1])))
    out = [sum(trs[:n]) / n]
    for tr in trs[n:]:
        out.append((out[-1] * (n - 1) + tr) / n)
    return [trs[0]] * (n - 1) + out


def supertrend(h, l, c, n=10, mult=3.0):
    atr = atr_wilder(h, l, c, n)
    up = [True] * len(c)
    fub = [0.0] * len(c)
    flb = [0.0] * len(c)
    for i in range(len(c)):
        mid = (h[i] + l[i]) / 2
        ub = mid + mult * atr[i]
        lb = mid - mult * atr[i]
        if i == 0:
            fub[i], flb[i] = ub, lb
            up[i] = c[i] >= mid
            continue
        fub[i] = ub if (ub < fub[i - 1] or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb if (lb > flb[i - 1] or c[i - 1] < flb[i - 1]) else flb[i - 1]
        up[i] = not (c[i] < flb[i]) if up[i - 1] else c[i] > fub[i]
    return up, atr


def adx14(h, l, c, n=14):
    trs, php, phm = [], [], []
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]),
                       abs(l[i] - c[i - 1])))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        php.append(up if up > dn and up > 0 else 0)
        phm.append(dn if dn > up and dn > 0 else 0)
    atr = [sum(trs[:n]) / n]
    for x in trs[n:]:
        atr.append((atr[-1] * (n - 1) + x) / n)
    dip = [sum(php[:n]) / n]
    dim = [sum(phm[:n]) / n]
    for x, y in zip(php[n:], phm[n:]):
        dip.append((dip[-1] * (n - 1) + x) / n)
        dim.append((dim[-1] * (n - 1) + y) / n)
    dxs = []
    for i in range(len(dip)):
        a = atr[i] or 1e-9
        p, m = 100 * dip[i] / a, 100 * dim[i] / a
        dxs.append(100 * abs(p - m) / (p + m) if (p + m) else 0)
    out = [0.0] * len(c)
    adv = [sum(dxs[:n]) / n]
    for x in dxs[n:]:
        adv.append((adv[-1] * (n - 1) + x) / n)
    idx = len(c) - len(adv)
    for i, v in enumerate(adv):
        out[idx + i] = v
    return out


def muat_state():
    if os.path.exists(F_STATE):
        with open(F_STATE) as f:
            return json.load(f)
    return {"arah": 0, "masuk": 0.0, "oz": 0.0, "saldo": SALDO_AWAL,
            "riwayat": []}


def simpan_state(s):
    with open(F_STATE, "w") as f:
        json.dump(s, f, indent=1)


def jurnal(t):
    j = []
    if os.path.exists(F_JURNAL):
        with open(F_JURNAL) as f:
            j = json.load(f)
    j.append(t)
    with open(F_JURNAL, "w") as f:
        json.dump(j[-500:], f, indent=1)


def hitung_sinyal():
    d1h = ambil_yahoo_1h()
    h4 = ke_h4(d1h)
    # bar terakhir mungkin belum tutup -> pakai 2 bar terakhir yang tutup
    h, l, c = h4["high"][:-1], h4["low"][:-1], h4["close"][:-1]
    st, _atr_band = supertrend(h, l, c, 7, 3.0)
    atr = atr_wilder(h, l, c, 10)  # unit risiko selalu 3x ATR(10), sama spt backtest
    adxv = adx14(h, l, c)
    arah_st = 1 if st[-1] else -1
    return {
        "harga": d1h["close"][-1],
        "arah_st": arah_st,
        "adx": round(adxv[-1], 1),
        "atr_h4": round(atr[-1], 2),
        "waktu_bar": datetime.fromtimestamp(
            h4["ts"][-2], timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def cmd_sinyal(paper=False):
    s = hitung_sinyal()
    st = muat_state()
    arah_sekarang = st["arah"]
    arah_target = s["arah_st"] if s["adx"] > 20 else 0
    nama = {1: "LONG", -1: "SHORT", 0: "FLAT"}
    print(f"Harga XAUUSD : ${s['harga']:.2f}")
    print(f"SuperTrend H4: {nama[s['arah_st']]} | ADX(14): {s['adx']} "
          f"({'lolos' if s['adx'] > 20 else 'chop -> FLAT'})")
    print(f"ATR H4       : ${s['atr_h4']:.2f} (unit risiko 3x = "
          f"${3 * s['atr_h4']:.2f}/oz)")
    print(f"Posisi paper : {nama[arah_sekarang]}")
    if arah_target == arah_sekarang:
        print("Sinyal       : TAHAN (tidak ada perubahan)")
        return
    print(f"Sinyal       : {'BUKA' if arah_target else 'TUTUP'} -> "
          f"{nama[arah_target]}")
    if not paper:
        print("(mode baca saja; tambah --paper untuk eksekusi paper)")
        return
    # tutup posisi lama
    if arah_sekarang != 0:
        pnl_oz = arah_sekarang * (s["harga"] - st["masuk"])
        pnl = pnl_oz * st["oz"] - BIAYA_OZ_RT * st["oz"]
        st["saldo"] += pnl
        st["riwayat"].append({"aksi": "TUTUP", "arah": nama[arah_sekarang],
                              "masuk": st["masuk"], "keluar": s["harga"],
                              "pnl": round(pnl, 2)})
        jurnal({"waktu": datetime.now(timezone.utc).isoformat(),
                "aksi": "TUTUP", "arah": nama[arah_sekarang],
                "harga": s["harga"], "pnl": round(pnl, 2),
                "saldo": round(st["saldo"], 2)})
        print(f"  -> posisi {nama[arah_sekarang]} ditutup, P/L ${pnl:.2f}")
    # buka posisi baru
    if arah_target != 0:
        risiko_usd = st["saldo"] * RISIKO_PERSEN / 100
        oz = risiko_usd / (3 * s["atr_h4"])
        st.update({"arah": arah_target, "masuk": s["harga"], "oz": oz})
        jurnal({"waktu": datetime.now(timezone.utc).isoformat(),
                "aksi": "BUKA", "arah": nama[arah_target],
                "harga": s["harga"], "oz": round(oz, 3),
                "saldo": round(st["saldo"], 2)})
        print(f"  -> {nama[arah_target]} {oz:.3f} oz @ ${s['harga']:.2f} "
              f"(risiko ${risiko_usd:.2f})")
    else:
        st.update({"arah": 0, "masuk": 0.0, "oz": 0.0})
    simpan_state(st)
    print(f"Saldo paper  : ${st['saldo']:.2f}")


def cmd_status():
    st = muat_state()
    nama = {1: "LONG", -1: "SHORT", 0: "FLAT"}
    print(f"Posisi: {nama[st['arah']]}")
    if st["arah"]:
        print(f"  masuk ${st['masuk']:.2f} | {st['oz']:.3f} oz")
    print(f"Saldo paper: ${st['saldo']:.2f}")
    print(f"Trade tercatat: {len(st['riwayat'])}")
    tot = sum(t["pnl"] for t in st["riwayat"] if t["aksi"] == "TUTUP")
    print(f"Total P/L: ${tot:.2f}")


if __name__ == "__main__":
    arg = sys.argv[1:]
    if not arg or arg[0] not in ("sinyal", "status"):
        print(__doc__)
    elif arg[0] == "status":
        cmd_status()
    else:
        cmd_sinyal(paper="--paper" in arg)
