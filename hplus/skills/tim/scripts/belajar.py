#!/usr/bin/env python3
"""
belajar.py — registry skill tiap agen (sistem belajar tim hplus).

Setiap agen punya inventaris skill di agen/<nama>/keterampilan.json.
Skill baru lahir sebagai 'usulan', harus diaudit Saka sebelum 'aktif'.

Perintah:
  tambah --agen --nama --tier --dari --file/--isi [--kontributor a,b]
  daftar [--agen] [--status usulan/aktif/nonaktif] [--tier]
  setujui --agen --nama            # usulan -> aktif (oleh Saka)
  tolak --agen --nama --catatan    # usulan ditolak (tetap tercatat)
  naik-versi --agen --nama --catatan
  ubah-tier --agen --nama --tier
  nonaktif / aktif --agen --nama
  info --agen --nama
"""

import argparse
import json
import os
import re
import sys
from datetime import date

try:
    import fcntl
    _ADA_FCNTL = True
except ImportError:  # non-Linux: kunci dinonaktifkan
    _ADA_FCNTL = False

DASAR = os.path.dirname(os.path.realpath(__file__))
TIM_DIR = os.path.dirname(DASAR)
AGEN_DIR = os.path.join(TIM_DIR, "agen")
TAHU_DIR = os.path.join(TIM_DIR, "pengetahuan")

TIER_VALID = {"dasar", "khusus", "dewa", "tambahan"}
STATUS_VALID = {"usulan", "aktif", "nonaktif", "ditolak"}


def agen_valid():
    return sorted(f[:-5] for f in os.listdir(AGEN_DIR) if f.endswith(".json"))


def reg_path(nama):
    return os.path.join(AGEN_DIR, nama, "keterampilan.json")


_KUNCI_REG = {}  # path -> handle lock (transaksi muat_reg -> simpan_reg)


def _kunci_reg(path):
    if not _ADA_FCNTL or path in _KUNCI_REG:
        return
    lk = open(path + ".lock", "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    _KUNCI_REG[path] = lk


def _lepas_reg(path=None):
    targets = [path] if path else list(_KUNCI_REG)
    for p in targets:
        lk = _KUNCI_REG.pop(p, None)
        if lk:
            try:
                fcntl.flock(lk, fcntl.LOCK_UN)
            finally:
                lk.close()


def muat_reg(nama):
    if nama not in agen_valid():
        raise ValueError(f"agen tidak dikenal: '{nama}' "
                         f"(pilih: {', '.join(agen_valid())})")
    path = reg_path(nama)
    _kunci_reg(path)  # dipegang sampai simpan_reg() / akhir perintah
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        return {"agen": nama, "keterampilan": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def simpan_reg(nama, data):
    path = reg_path(nama)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        _lepas_reg(path)


def cari(reg, nama_skill):
    for s in reg["keterampilan"]:
        if s["nama"] == nama_skill:
            return s
    return None


def slug(nama):
    s = re.sub(r"[^a-z0-9]+", "-", nama.lower()).strip("-")
    if not s:
        raise ValueError("nama skill tidak valid")
    return s


def cmd_tambah(args):
    if args.tier not in TIER_VALID:
        print(f"ERROR: tier tidak valid: {args.tier} "
              f"(pilih: {', '.join(sorted(TIER_VALID))})")
        return 1
    reg = muat_reg(args.agen)
    nama = slug(args.nama)
    if cari(reg, nama):
        print(f"ERROR: skill '{nama}' sudah ada di {args.agen} "
              f"(pakai naik-versi untuk upgrade).")
        return 1
    isi = args.isi
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            isi = f.read()
    if not isi:
        print("ERROR: isi skill kosong (pakai --file atau --isi).")
        return 1
    # tulis file pengetahuan
    folder = os.path.join(TAHU_DIR, args.agen)
    os.makedirs(folder, exist_ok=True)
    fp = os.path.join(folder, f"{nama}.md")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(isi if isi.endswith("\n") else isi + "\n")
    reg["keterampilan"].append({
        "nama": nama,
        "tier": args.tier,
        "versi": 1,
        "status": "usulan",
        "dari": args.dari or "-",
        "kontributor": args.kontributor or args.agen,
        "diperbarui": date.today().isoformat(),
        "riwayat": [f"v1 diusulkan dari {args.dari or '-'}"],
    })
    simpan_reg(args.agen, reg)
    print(f"OK: skill '{nama}' ({args.tier}) diusulkan untuk {args.agen}.")
    print("Menunggu audit Saka → 'belajar.py setujui' untuk mengaktifkan.")
    return 0


def cmd_daftar(args):
    agens = [args.agen] if args.agen else agen_valid()
    ada = False
    for ag in agens:
        reg = muat_reg(ag)
        items = reg["keterampilan"]
        if args.status:
            items = [s for s in items if s["status"] == args.status]
        if args.tier:
            items = [s for s in items if s["tier"] == args.tier]
        if not items:
            continue
        ada = True
        print(f"== {ag} ==")
        for s in items:
            print(f"  [{s['status']:8s}] {s['nama']:28s} "
                  f"{s['tier']:9s} v{s['versi']}")
    if not ada:
        print("(tidak ada skill)")
    return 0


def cmd_setujui(args):
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    if s["status"] != "usulan":
        print(f"ERROR: hanya 'usulan' yang bisa disetujui "
              f"(status: {s['status']}).")
        return 1
    s["status"] = "aktif"
    s["diperbarui"] = date.today().isoformat()
    s["riwayat"].append("disetujui Saka → aktif")
    simpan_reg(args.agen, reg)
    print(f"OK: '{s['nama']}' aktif ✅")
    return 0


def cmd_tolak(args):
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    if s["status"] != "usulan":
        print(f"ERROR: hanya 'usulan' yang bisa ditolak.")
        return 1
    s["status"] = "ditolak"
    s["diperbarui"] = date.today().isoformat()
    s["riwayat"].append(f"ditolak Saka: {args.catatan or '-'}")
    simpan_reg(args.agen, reg)
    print(f"OK: '{s['nama']}' ditolak ❌ — tercatat, perbaiki & ajukan lagi.")
    return 0


def cmd_naik_versi(args):
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    s["versi"] += 1
    s["diperbarui"] = date.today().isoformat()
    s["riwayat"].append(f"v{s['versi']}: {args.catatan or '-'}")
    simpan_reg(args.agen, reg)
    print(f"OK: '{s['nama']}' naik ke v{s['versi']}")
    return 0


def cmd_ubah_tier(args):
    if args.tier not in TIER_VALID:
        print(f"ERROR: tier tidak valid: {args.tier}")
        return 1
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    lama = s["tier"]
    s["tier"] = args.tier
    s["diperbarui"] = date.today().isoformat()
    s["riwayat"].append(f"tier {lama} → {args.tier}"
                        + (f": {args.catatan}" if args.catatan else ""))
    simpan_reg(args.agen, reg)
    print(f"OK: '{s['nama']}' tier {lama} → {args.tier}")
    return 0


def cmd_status(args, ke):
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    s["status"] = ke
    s["diperbarui"] = date.today().isoformat()
    s["riwayat"].append(f"status → {ke}")
    simpan_reg(args.agen, reg)
    print(f"OK: '{s['nama']}' → {ke}")
    return 0


def cmd_info(args):
    reg = muat_reg(args.agen)
    s = cari(reg, slug(args.nama))
    if not s:
        print(f"ERROR: skill '{args.nama}' tidak ada di {args.agen}")
        return 1
    print(f"Skill: {s['nama']}  ({args.agen})")
    print(f"  tier: {s['tier']} | versi: v{s['versi']} | status: {s['status']}")
    print(f"  dari: {s['dari']} | kontributor: {s['kontributor']}")
    print(f"  diperbarui: {s['diperbarui']}")
    print("  riwayat:")
    for r in s["riwayat"]:
        print(f"    - {r}")
    fp = os.path.join(TAHU_DIR, args.agen, f"{s['nama']}.md")
    print(f"  file: {fp} {'(ada)' if os.path.isfile(fp) else '(HILANG!)'}")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="belajar.py",
        description="Registry skill tiap agen: tambah, setujui, upgrade.")
    sub = p.add_subparsers(dest="aksi", required=True)

    s = sub.add_parser("tambah", help="Usulkan skill baru")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.add_argument("--tier", required=True, help="dasar/khusus/dewa/tambahan")
    s.add_argument("--dari", help="ID tugas asal (mis. T-003)")
    s.add_argument("--file", help="File .md isi skill")
    s.add_argument("--isi", help="Isi skill langsung")
    s.add_argument("--kontributor", help="Mis. 'koda,vera' untuk skill gabungan")
    s.set_defaults(func=cmd_tambah)

    s = sub.add_parser("daftar", help="Daftar skill")
    s.add_argument("--agen")
    s.add_argument("--status", choices=sorted(STATUS_VALID))
    s.add_argument("--tier", choices=sorted(TIER_VALID))
    s.set_defaults(func=cmd_daftar)

    s = sub.add_parser("setujui", help="Saka: usulan → aktif")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.set_defaults(func=cmd_setujui)

    s = sub.add_parser("tolak", help="Saka: tolak usulan")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.add_argument("--catatan")
    s.set_defaults(func=cmd_tolak)

    s = sub.add_parser("naik-versi", help="Upgrade versi skill")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.add_argument("--catatan")
    s.set_defaults(func=cmd_naik_versi)

    s = sub.add_parser("ubah-tier", help="Ubah tier skill")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.add_argument("--tier", required=True)
    s.add_argument("--catatan")
    s.set_defaults(func=cmd_ubah_tier)

    s = sub.add_parser("nonaktif", help="Nonaktifkan skill")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.set_defaults(func=lambda a: cmd_status(a, "nonaktif"))

    s = sub.add_parser("aktif", help="Aktifkan kembali skill")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.set_defaults(func=lambda a: cmd_status(a, "aktif"))

    s = sub.add_parser("info", help="Detail + riwayat skill")
    s.add_argument("--agen", required=True)
    s.add_argument("--nama", required=True)
    s.set_defaults(func=cmd_info)

    args = p.parse_args()
    try:
        return args.func(args)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        _lepas_reg()  # jangan bocorkan kunci, bahkan saat error


if __name__ == "__main__":
    sys.exit(main())
