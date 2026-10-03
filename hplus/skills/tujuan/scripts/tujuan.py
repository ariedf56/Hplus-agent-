#!/usr/bin/env python3
"""
tujuan.py — pelacak tujuan ala tab Goals. Data disimpan lokal (data.json).

Pemakaian:
    python3 tujuan.py tambah "Belajar SSH" --target 2026-12-31
    python3 tujuan.py daftar
    python3 tujuan.py daftar --semua
    python3 tujuan.py progres 1 "Berhasil login SSH pertama"
    python3 tujuan.py selesai 1
"""
import datetime
import json
import os
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def muat():
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    return {"berikutnya": 1, "tujuan": []}


def simpan(d):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def cmd_tambah(nama, target=""):
    d = muat()
    tid = d["berikutnya"]
    d["tujuan"].append(
        {
            "id": tid,
            "nama": nama,
            "target": target,
            "status": "aktif",
            "dibuat": datetime.date.today().isoformat(),
            "progres": [],
        }
    )
    d["berikutnya"] = tid + 1
    simpan(d)
    print(f"Tujuan #{tid} dicatat: {nama}")


def cmd_daftar(semua=False):
    d = muat()
    daftar = d["tujuan"] if semua else [t for t in d["tujuan"]
                                       if t["status"] == "aktif"]
    if not daftar:
        print("Belum ada tujuan aktif.")
        return
    for t in daftar:
        tandai = "✓" if t["status"] == "selesai" else "•"
        print(f"{tandai} #{t['id']} {t['nama']}"
              f"{' (target: ' + t['target'] + ')' if t['target'] else ''}")
        for p in t["progres"][-3:]:
            print(f"    - [{p['tanggal']}] {p['catatan']}")


def cmd_progres(tid, catatan):
    d = muat()
    for t in d["tujuan"]:
        if t["id"] == tid:
            t["progres"].append({"tanggal": datetime.date.today().isoformat(),
                                "catatan": catatan})
            simpan(d)
            print(f"Progres #{tid} dicatat.")
            return
    print(f"Tujuan #{tid} tidak ditemukan.")


def cmd_selesai(tid):
    d = muat()
    for t in d["tujuan"]:
        if t["id"] == tid:
            t["status"] = "selesai"
            simpan(d)
            print(f"Tujuan #{tid} selesai. Kerja bagus!")
            return
    print(f"Tujuan #{tid} tidak ditemukan.")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    c = argv[1]
    if c == "tambah" and len(argv) >= 3:
        target = ""
        if "--target" in argv:
            target = argv[argv.index("--target") + 1]
        cmd_tambah(argv[2], target)
    elif c == "daftar":
        cmd_daftar(semua="--semua" in argv)
    elif c == "progres" and len(argv) >= 4:
        cmd_progres(int(argv[2]), argv[3])
    elif c == "selesai" and len(argv) >= 3:
        cmd_selesai(int(argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
