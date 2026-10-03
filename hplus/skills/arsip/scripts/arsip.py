#!/usr/bin/env python3
"""
arsip.py — arsip file ala tab Library. Menyimpan salinan file ke
gudang lokal yang terkategorikan + indeks yang bisa dicari.

Pemakaian:
    python3 arsip.py simpan /tmp/laporan.pdf --kategori laporan --ket "Laporan mingguan"
    python3 arsip.py daftar
    python3 arsip.py daftar --kategori laporan
    python3 arsip.py daftar --cari wifilab
"""
import json
import os
import shutil
import sys
import datetime

DASAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gudang")
INDEKS = os.path.join(DASAR, "indeks.json")


def muat_indeks():
    if os.path.exists(INDEKS):
        with open(INDEKS, encoding="utf-8") as f:
            return json.load(f)
    return {"berikutnya": 1, "entri": []}


def simpan_indeks(d):
    os.makedirs(DASAR, exist_ok=True)
    with open(INDEKS, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def cmd_simpan(path, kategori="umum", ket=""):
    if not os.path.isfile(path):
        print(f"File tidak ditemukan: {path}")
        sys.exit(1)
    d = muat_indeks()
    eid = d["berikutnya"]
    nama = os.path.basename(path)
    folder = os.path.join(DASAR, kategori)
    os.makedirs(folder, exist_ok=True)
    tujuan = os.path.join(folder, f"{eid}_{nama}")
    shutil.copy2(path, tujuan)
    d["entri"].append({
        "id": eid,
        "nama": nama,
        "kategori": kategori,
        "keterangan": ket,
        "lokasi": tujuan,
        "disimpan": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    d["berikutnya"] = eid + 1
    simpan_indeks(d)
    print(f"Tersimpan sebagai arsip #{eid} [{kategori}]: {nama}")


def cmd_daftar(kategori="", cari=""):
    d = muat_indeks()
    entri = d["entri"]
    if kategori:
        entri = [e for e in entri if e["kategori"] == kategori]
    if cari:
        c = cari.lower()
        entri = [e for e in entri
                 if c in e["nama"].lower() or c in e["keterangan"].lower()]
    if not entri:
        print("Arsip kosong.")
        return
    for e in entri:
        print(f"#{e['id']} [{e['kategori']}] {e['nama']}"
              f"{' — ' + e['keterangan'] if e['keterangan'] else ''}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    c = argv[1]
    opt = {}
    sisa = []
    i = 2
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            sisa.append(argv[i])
            i += 1
    if c == "simpan" and sisa:
        cmd_simpan(sisa[0], opt.get("kategori", "umum"), opt.get("ket", ""))
    elif c == "daftar":
        cmd_daftar(opt.get("kategori", ""), opt.get("cari", ""))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
