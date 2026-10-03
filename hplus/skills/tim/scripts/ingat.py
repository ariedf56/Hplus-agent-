#!/usr/bin/env python3
"""
ingat.py — memori tim hplus 🧠.

Agen tidak lagi amnesia: kejadian, preferensi user, fakta penting, dan
pelajaran dari kegagalan dicatat dan bisa dicari. Memori yang relevan
disuntik otomatis ke setiap delegasi (lihat delegasikan.py).

Penyimpanan: skills/tim/memori/<agen>.json + bersama.json
Konteks tim: skills/tim/konteks.md (fokus, keputusan, instruksi, preferensi)

Perintah:
  catat --agen <nama|bersama> --topik ... --isi ... [--jenis fakta|preferensi|pelajaran|peristiwa]
  cari <kata kunci> [--agen <nama>] [--batas 5]
  daftar [--agen <nama>] [--jenis ...]
  hapus --agen <nama> --id <ID>
  pelajaran [--kata ...]              # semua pelajaran (auto dari audit gagal)
  konteks                             # tampilkan konteks tim
  konteks-tambah --bagian fokus|keputusan|instruksi|preferensi --isi ...
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

DASAR = os.path.dirname(os.path.realpath(__file__))
TIM_DIR = os.path.dirname(DASAR)
MEMDIR = os.path.join(TIM_DIR, "memori")
KONTEKS = os.path.join(TIM_DIR, "konteks.md")
JENIS_VALID = {"fakta", "preferensi", "pelajaran", "peristiwa"}
BAGIAN_VALID = {"fokus": "Fokus saat ini",
                "keputusan": "Keputusan terakhir",
                "instruksi": "Instruksi yang berlaku",
                "preferensi": "Preferensi user"}

try:
    import fcntl
    _ADA_FCNTL = True
except ImportError:
    _ADA_FCNTL = False

_KUNCI = {}


def _kunci(path):
    if not _ADA_FCNTL or path in _KUNCI:
        return
    lk = open(path + ".lock", "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    _KUNCI[path] = lk


def _lepas(path=None):
    for p in ([path] if path else list(_KUNCI)):
        lk = _KUNCI.pop(p, None)
        if lk:
            try:
                fcntl.flock(lk, fcntl.LOCK_UN)
            finally:
                lk.close()


def agen_valid():
    adir = os.path.join(TIM_DIR, "agen")
    return sorted(f[:-5] for f in os.listdir(adir) if f.endswith(".json"))


def _path(agen):
    return os.path.join(MEMDIR, f"{agen}.json")


def _baca(agen):
    p = _path(agen)
    if not os.path.isfile(p):
        return {"agen": agen, "memori": []}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _tulis(agen, data):
    p = _path(agen)
    os.makedirs(MEMDIR, exist_ok=True)
    _kunci(p)
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    finally:
        _lepas(p)


def _validasi_agen(agen):
    if agen != "bersama" and agen not in agen_valid():
        raise ValueError(f"agen tidak dikenal: '{agen}' "
                         f"(atau 'bersama' untuk memori tim)")


# ---------- API (bisa diimpor tim.py / delegasikan.py) ----------
def catat_memori(agen, topik, isi, jenis="fakta"):
    """Catat satu memori. Kembalikan ID (M-001...)."""
    _validasi_agen(agen)
    if jenis not in JENIS_VALID:
        raise ValueError(f"jenis tidak valid: {jenis}")
    data = _baca(agen)
    mid = f"M-{len(data['memori']) + 1:03d}"
    data["memori"].append({
        "id": mid,
        "topik": topik.strip(),
        "isi": isi.strip(),
        "jenis": jenis,
        "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _tulis(agen, data)
    return mid


_STOP = {"yang", "dan", "untuk", "dengan", "dari", "ini", "itu", "ada",
        "pada", "dalam", "secara", "agar", "bisa", "akan", "telah",
        "sudah", "belum", "jangan", "saya", "kamu", "kita", "mereka",
        "the", "and", "with", "dari"}


def _skor(teks, kunci):
    t = teks.lower()
    return sum(len(re.findall(rf"\b{re.escape(k)}\b", t)) for k in kunci)


def cari_memori(query, agen=None, batas=5, jenis=None):
    """Cari memori paling relevan dengan query (skor overlap kata kunci)."""
    kunci = [w for w in re.findall(r"[a-zA-Z]{4,}", query.lower())
             if w not in _STOP]
    if not kunci:
        kunci = re.findall(r"[a-zA-Z]+", query.lower())
    targets = [agen] if agen else (["bersama"] + agen_valid())
    hasil = []
    for ag in targets:
        p = _path(ag)
        if not os.path.isfile(p):
            continue
        data = _baca(ag)
        for m in data["memori"]:
            if jenis and m["jenis"] != jenis:
                continue
            s = _skor(m["topik"] + " " + m["isi"], kunci)
            # pelajaran selalu sedikit diutamakan (mencegah ulangi salah)
            if m["jenis"] == "pelajaran":
                s += 1
            if s > 0:
                hasil.append((s, ag, m))
    hasil.sort(key=lambda x: -x[0])
    return [{"agen": ag, **m, "skor": s} for s, ag, m in hasil[:batas]]


def baca_konteks(max_baris=40):
    """Isi konteks.md (dipotong agar hemat)."""
    if not os.path.isfile(KONTEKS):
        return "(konteks tim belum ditulis)"
    with open(KONTEKS, encoding="utf-8") as f:
        baris = f.read().splitlines()
    if len(baris) > max_baris:
        baris = baris[:max_baris] + ["... (dipotong)"]
    return "\n".join(baris)


# ---------- CLI ----------
def cmd_catat(args):
    try:
        mid = catat_memori(args.agen, args.topik, args.isi, args.jenis)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    print(f"OK: memori {mid} tercatat untuk {args.agen} 🧠")
    return 0


def cmd_cari(args):
    try:
        hasil = cari_memori(args.kata, agen=args.agen, batas=args.batas)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    if not hasil:
        print("(tidak ada memori yang cocok)")
        return 0
    for h in hasil:
        print(f"[{h['jenis']}|{h['agen']}] {h['id']} {h['topik']}")
        print(f"    {h['isi'][:200]}")
    return 0


def cmd_daftar(args):
    agens = [args.agen] if args.agen else (["bersama"] + agen_valid())
    ada = False
    for ag in agens:
        if ag != "bersama" and ag not in agen_valid():
            print(f"ERROR: agen tidak dikenal: {ag}")
            return 1
        data = _baca(ag)
        mem = data["memori"]
        if args.jenis:
            mem = [m for m in mem if m["jenis"] == args.jenis]
        for m in mem:
            ada = True
            print(f"{m['id']} [{m['jenis']}|{ag}] {m['topik']}")
    if not ada:
        print("(belum ada memori)")
    return 0


def cmd_hapus(args):
    try:
        _validasi_agen(args.agen)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    data = _baca(args.agen)
    awal = len(data["memori"])
    data["memori"] = [m for m in data["memori"] if m["id"] != args.id.upper()]
    if len(data["memori"]) == awal:
        print(f"ERROR: {args.id.upper()} tidak ada di {args.agen}")
        return 1
    _tulis(args.agen, data)
    print(f"OK: {args.id.upper()} dihapus dari memori {args.agen}.")
    return 0


def cmd_pelajaran(args):
    hasil = cari_memori(args.kata or "gagal salah pelajaran hindari",
                        jenis="pelajaran", batas=20)
    if not hasil:
        print("(belum ada pelajaran tercatat)")
        return 0
    for h in hasil:
        print(f"📝 [{h['agen']}] {h['topik']}\n    {h['isi'][:250]}\n")
    return 0


def cmd_konteks(args):
    print(baca_konteks())
    return 0


def cmd_konteks_tambah(args):
    if args.bagian not in BAGIAN_VALID:
        print(f"ERROR: bagian tidak valid (fokus/keputusan/instruksi/preferensi)")
        return 1
    judul = BAGIAN_VALID[args.bagian]
    baris = []
    if os.path.isfile(KONTEKS):
        with open(KONTEKS, encoding="utf-8") as f:
            baris = f.read().splitlines()
    else:
        baris = ["# Konteks Tim 📌", ""]
    # cari section, atau buat baru di akhir
    idx = next((i for i, b in enumerate(baris)
                if b.strip() == f"## {judul}"), None)
    entri = f"- [{datetime.now().strftime('%Y-%m-%d')}] {args.isi}"
    if idx is None:
        baris += ["", f"## {judul}", entri]
    else:
        baris.insert(idx + 1, entri)
    with open(KONTEKS, "w", encoding="utf-8") as f:
        f.write("\n".join(baris) + "\n")
    print(f"OK: konteks [{args.bagian}] ditambah 📌")
    return 0


def main():
    p = argparse.ArgumentParser(prog="ingat.py",
                                description="Memori tim hplus 🧠")
    sub = p.add_subparsers(dest="aksi", required=True)

    s = sub.add_parser("catat", help="Catat memori baru")
    s.add_argument("--agen", required=True, help="nama agen / bersama")
    s.add_argument("--topik", required=True)
    s.add_argument("--isi", required=True)
    s.add_argument("--jenis", default="fakta",
                   help="fakta/preferensi/pelajaran/peristiwa")
    s.set_defaults(func=cmd_catat)

    s = sub.add_parser("cari", help="Cari memori relevan")
    s.add_argument("kata", help="Kata kunci")
    s.add_argument("--agen", help="Batasi ke agen tertentu")
    s.add_argument("--batas", type=int, default=5)
    s.set_defaults(func=cmd_cari)

    s = sub.add_parser("daftar", help="Daftar memori")
    s.add_argument("--agen", help="nama agen / kosongkan = semua")
    s.add_argument("--jenis", help="Filter jenis")
    s.set_defaults(func=cmd_daftar)

    s = sub.add_parser("hapus", help="Hapus satu memori")
    s.add_argument("--agen", required=True)
    s.add_argument("--id", required=True, help="mis. M-003")
    s.set_defaults(func=cmd_hapus)

    s = sub.add_parser("pelajaran", help="Daftar pelajaran dari kegagalan")
    s.add_argument("--kata", help="Filter kata kunci")
    s.set_defaults(func=cmd_pelajaran)

    s = sub.add_parser("konteks", help="Tampilkan konteks tim")
    s.set_defaults(func=cmd_konteks)

    s = sub.add_parser("konteks-tambah", help="Tambah entri konteks tim")
    s.add_argument("--bagian", required=True,
                   help="fokus/keputusan/instruksi/preferensi")
    s.add_argument("--isi", required=True)
    s.set_defaults(func=cmd_konteks_tambah)

    args = p.parse_args()
    try:
        return args.func(args)
    finally:
        _lepas()


if __name__ == "__main__":
    sys.exit(main())
