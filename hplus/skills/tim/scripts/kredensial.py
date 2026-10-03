#!/usr/bin/env python3
"""
kredensial.py — brankas kredensial Ari 🔑.

Menjaga & mengelola kredensial APAPUN: akun web, API key, token, dsb.
File: skills/tim/agen/ari/kredensial.json (mode 600 — hanya pemilik).

ATURAN KERAS:
- Rahasia TIDAK PERNAH tampil di: papan tugas, chat, laporan, screenshot,
  log. Hanya di kredensial.json dan di memori proses saat dipakai.
- Satu-satunya cara memakai rahasia untuk login web: 'isi'
  (langsung ke browser, tanpa mencetak).
- 'ambil' mencetak rahasia ke stdout — HANYA untuk kebutuhan agen yang
  sah (mis. Koda butuh API key untuk konfigurasi), JANGAN diteruskan
  ke papan/chat/laporan.

Perintah:
  simpan --label ... --jenis ... --rahasia ... [--situs] [--identitas] [--catatan]
  daftar [--jenis]
  cek --label
  ambil --label
  isi --label --identitas-sel SEL --rahasia-sel SEL [--kirim-sel SEL]
  hapus --label --ya
"""
import argparse
import json
import os
import sys

DASAR = os.path.dirname(os.path.realpath(__file__))
VAULT = os.path.realpath(os.path.join(DASAR, "..", "agen", "ari",
                                      "kredensial.json"))
JENIS_VALID = {"akun-web", "api-key", "token", "lainnya"}


def muat():
    if not os.path.isfile(VAULT):
        return {"kredensial": []}
    with open(VAULT, "r", encoding="utf-8") as f:
        return json.load(f)


def simpan_data(data):
    os.makedirs(os.path.dirname(VAULT), exist_ok=True)
    # cadangan otomatis: simpan 5 versi terakhir sebelum tulis
    if os.path.isfile(VAULT):
        import glob
        from datetime import datetime
        bak = VAULT + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(VAULT, "rb") as fsrc, open(bak, "wb") as fdst:
            fdst.write(fsrc.read())
        os.chmod(bak, 0o600)
        lama = sorted(glob.glob(VAULT + ".bak-*"))
        for buang in lama[:-5]:
            os.remove(buang)
    tmp = VAULT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, VAULT)
    os.chmod(VAULT, 0o600)


def cari(data, label):
    for k in data["kredensial"]:
        if k["label"] == label:
            return k
    return None


def cmd_simpan(args):
    if args.jenis not in JENIS_VALID:
        print(f"ERROR: jenis tidak valid: {args.jenis} "
              f"(pilih: {', '.join(sorted(JENIS_VALID))})")
        return 1
    for f in ("label", "rahasia"):
        if not getattr(args, f):
            print(f"ERROR: --{f} wajib diisi")
            return 1
    data = muat()
    if cari(data, args.label):
        print(f"ERROR: label '{args.label}' sudah ada — hapus dulu bila ingin ganti.")
        return 1
    from datetime import datetime
    data["kredensial"].append({
        "label": args.label,
        "jenis": args.jenis,
        "situs": args.situs or "",
        "identitas": args.identitas or "",
        "rahasia": args.rahasia,
        "catatan": args.catatan or "",
        "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    simpan_data(data)
    print(f"OK: kredensial '{args.label}' ({args.jenis}) tersimpan 🔑 "
          f"(file mode 600)")
    print("INGAT: rahasia tidak pernah ditulis ke papan/chat/laporan.")
    return 0


def cmd_daftar(args):
    data = muat()
    kred = data["kredensial"]
    if args.jenis:
        kred = [k for k in kred if k["jenis"] == args.jenis]
    if not kred:
        print("(belum ada kredensial)")
        return 0
    for k in kred:
        extra = f" | {k['situs']}" if k["situs"] else ""
        ident = f" | {k['identitas']}" if k["identitas"] else ""
        print(f"🔑 {k['label']} [{k['jenis']}]{extra}{ident} "
              f"(dibuat {k['dibuat']})")
    print(f"\nTotal: {len(kred)} (rahasia tidak ditampilkan)")
    return 0


def cmd_cek(args):
    data = muat()
    k = cari(data, args.label)
    if k:
        print(f"ADA: '{args.label}' ({k['jenis']})")
        return 0
    print(f"TIDAK ADA: '{args.label}'")
    return 1


def cmd_ambil(args):
    data = muat()
    k = cari(data, args.label)
    if not k:
        print(f"ERROR: label '{args.label}' tidak ada")
        return 1
    print("⚠️  RAHASIA — hanya untuk kebutuhan agen yang sah. "
          "JANGAN teruskan ke papan/chat/laporan.")
    print(k["rahasia"])
    return 0


def cmd_isi(args):
    """Isi kredensial ke browser hidup (daemon) tanpa mencetak rahasia."""
    data = muat()
    k = cari(data, args.label)
    if not k:
        print(f"ERROR: label '{args.label}' tidak ada — catat dulu via 'simpan'.")
        return 1
    sys.path.insert(0, os.path.realpath(
        os.path.join(DASAR, "..", "..", "browser", "scripts")))
    try:
        import browser as B
    except ImportError as e:
        print(f"ERROR: skill browser tidak ditemukan ({e})")
        return 1
    if not B.daemon_hidup():
        print("ERROR: daemon browser mati — 'browser.py daemon start' dulu "
              "(atau buka via dashboard).")
        return 1
    if k["identitas"]:
        r = B.via_daemon("isi", {"selector": args.identitas_sel,
                                 "teks": k["identitas"]})
        if not r:
            print("ERROR: gagal mengisi identitas")
            return 1
    r = B.via_daemon("isi", {"selector": args.rahasia_sel,
                             "teks": k["rahasia"]})
    if not r:
        print("ERROR: gagal mengisi rahasia")
        return 1
    if args.kirim_sel:
        B.via_daemon("klik", {"selector": args.kirim_sel})
    print(f"OK: kredensial '{args.label}' diisikan ke form "
          f"(rahasia tidak ditampilkan) ✅")
    return 0


def cmd_hapus(args):
    data = muat()
    k = cari(data, args.label)
    if not k:
        print(f"ERROR: label '{args.label}' tidak ada")
        return 1
    if not args.ya:
        print(f"Yakin hapus '{args.label}'? Ulangi dengan --ya.")
        return 1
    data["kredensial"] = [x for x in data["kredensial"]
                          if x["label"] != args.label]
    simpan_data(data)
    print(f"OK: '{args.label}' dihapus.")
    return 0


def main():
    p = argparse.ArgumentParser(prog="kredensial.py",
                                description="Brankas kredensial Ari 🔑")
    sub = p.add_subparsers(dest="aksi", required=True)

    s = sub.add_parser("simpan", help="Simpan kredensial baru")
    s.add_argument("--label", required=True, help="Nama unik, mis. gmail-utama")
    s.add_argument("--jenis", required=True,
                   help="akun-web/api-key/token/lainnya")
    s.add_argument("--rahasia", required=True, help="Password/key/token")
    s.add_argument("--situs", help="URL situs (untuk akun-web)")
    s.add_argument("--identitas", help="Email/username")
    s.add_argument("--catatan", help="Catatan bebas (tanpa rahasia!)")
    s.set_defaults(func=cmd_simpan)

    s = sub.add_parser("daftar", help="Daftar kredensial (tanpa rahasia)")
    s.add_argument("--jenis", help="Filter jenis")
    s.set_defaults(func=cmd_daftar)

    s = sub.add_parser("cek", help="Cek label ada/tidak")
    s.add_argument("--label", required=True)
    s.set_defaults(func=cmd_cek)

    s = sub.add_parser("ambil", help="Ambil rahasia (stdout, hati-hati!)")
    s.add_argument("--label", required=True)
    s.set_defaults(func=cmd_ambil)

    s = sub.add_parser("isi", help="Isikan ke form browser (tanpa tampil)")
    s.add_argument("--label", required=True)
    s.add_argument("--identitas-sel", required=True,
                   help="Selector field email/username")
    s.add_argument("--rahasia-sel", required=True,
                   help="Selector field password")
    s.add_argument("--kirim-sel", help="Selector tombol submit (opsional)")
    s.set_defaults(func=cmd_isi)

    s = sub.add_parser("hapus", help="Hapus kredensial")
    s.add_argument("--label", required=True)
    s.add_argument("--ya", action="store_true", help="Konfirmasi hapus")
    s.set_defaults(func=cmd_hapus)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
