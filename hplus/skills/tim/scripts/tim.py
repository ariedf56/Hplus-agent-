#!/usr/bin/env python3
"""
Papan tugas tim hplus — antrean kerja para agen.

Setiap tugas punya: id (T-001...), judul, pemilik (nara/koda/vera/raka/tara),
prioritas, status (antri -> jalan -> selesai), detail, dan hasil.

Data tersimpan di tugas.json di folder skill ini (stdlib saja).
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import fcntl
    _ADA_FCNTL = True
except ImportError:  # non-Linux: kunci dinonaktifkan (target = VPS Linux)
    _ADA_FCNTL = False

AGEN_VALID = {"nara", "koda", "vera", "raka", "tara", "saka", "ari"}
PRIORITAS_VALID = {"rendah", "sedang", "tinggi", "mendesak"}
STATUS_VALID = {"antri", "jalan", "selesai"}
BOBOT = {"mendesak": 0, "tinggi": 1, "sedang": 2, "rendah": 3}

PAPAN = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tugas.json")


def _kunci_ex():
    """Ambil exclusive lock antar-proses (None bila fcntl tak ada)."""
    if not _ADA_FCNTL:
        return None
    lk = open(PAPAN + ".lock", "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    return lk


def _lepas(lk):
    if lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_UN)
        finally:
            lk.close()


_KUNCI = None  # lock transaksi tulis, dipegang muat() -> simpan()/lepas()


def _baca_data():
    if not os.path.isfile(PAPAN):
        return {"berikutnya": 1, "tugas": []}
    with open(PAPAN, "r", encoding="utf-8") as f:
        return json.load(f)


def baca():
    """Baca read-only: tunggu penulis selesai, baca cepat, lepas."""
    lk = _kunci_ex()
    try:
        return _baca_data()
    finally:
        _lepas(lk)


def muat():
    """Mulai transaksi tulis: kunci eksklusif dipegang sampai simpan()."""
    global _KUNCI
    _KUNCI = _kunci_ex()
    return _baca_data()


def simpan(data):
    """Tulis atomik (tmp + replace) lalu lepaskan kunci."""
    global _KUNCI
    try:
        tmp = PAPAN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, PAPAN)
    finally:
        _lepas(_KUNCI)
        _KUNCI = None


def lepas():
    """Lepaskan kunci bila masih dipegang (dijamin via finally di main)."""
    global _KUNCI
    _lepas(_KUNCI)
    _KUNCI = None


def cari(data, tid):
    tid = tid.upper()
    for t in data["tugas"]:
        if t["id"] == tid:
            return t
    return None


def cmd_tambah(args):
    if args.untuk not in AGEN_VALID:
        print(f"ERROR: agen tidak dikenal: {args.untuk} "
              f"(pilih: {', '.join(sorted(AGEN_VALID))})")
        return 1
    if args.prioritas not in PRIORITAS_VALID:
        print(f"ERROR: prioritas tidak valid: {args.prioritas}")
        return 1
    data = muat()
    tid = f"T-{data['berikutnya']:03d}"
    data["berikutnya"] += 1
    data["tugas"].append({
        "id": tid,
        "judul": args.judul,
        "untuk": args.untuk,
        "prioritas": args.prioritas,
        "status": "antri",
        "detail": args.detail or "",
        "hasil": "",
        "minta_bantuan": None,  # {"ke": "user"/agen, "pesan": ..., "pada": ...}
        "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    simpan(data)
    print(f"OK: {tid} ditambahkan untuk {args.untuk} "
          f"(prioritas {args.prioritas})")
    return 0


def cmd_daftar(args):
    data = baca()
    tugas = data["tugas"]
    if args.status:
        tugas = [t for t in tugas if t["status"] == args.status]
    if args.untuk:
        tugas = [t for t in tugas if t["untuk"] == args.untuk]
    if not tugas:
        print("(tidak ada tugas)")
        return 0
    tugas = sorted(tugas, key=lambda t: (BOBOT[t["prioritas"]], t["id"]))
    ikon = {"antri": "⏳", "jalan": "🔨", "selesai": "✅"}
    for t in tugas:
        butuh = " 🙋 BUTUH" if t.get("minta_bantuan") else ""
        print(f"{ikon[t['status']]} {t['id']} [{t['prioritas']}] "
              f"({t['untuk']}) {t['judul']}{butuh}")
        if t.get("minta_bantuan"):
            mb = t["minta_bantuan"]
            print(f"    🙋 minta ke {mb['ke']}: {mb['pesan'][:160]}")
        if args.detail and t["detail"]:
            print(f"    detail: {t['detail']}")
        if t["status"] == "selesai" and t["hasil"] and args.detail:
            print(f"    hasil: {t['hasil'][:200]}")
        if args.detail and t.get("audit"):
            for a in t["audit"]:
                mark = "✅" if a["vonis"] == "lulus" else "❌"
                print(f"    audit {mark} [{a['vonis']}] oleh {a['oleh']}: "
                      f"{a['catatan'][:160]}")
    return 0


def cmd_ambil(args):
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    if t["status"] == "selesai":
        print(f"ERROR: {t['id']} sudah selesai — buat tugas baru jika perlu.")
        return 1
    if t["status"] == "jalan":
        print(f"ERROR: {t['id']} sedang dikerjakan ({t['untuk']}).")
        return 1
    t["status"] = "jalan"
    t["untuk"] = args.oleh  # siapa pun boleh mengambil alih tugas antri
    simpan(data)
    print(f"OK: {t['id']} diambil oleh {args.oleh} → status jalan")
    if t["detail"]:
        print(f"detail: {t['detail']}")
    return 0


def cmd_selesai(args):
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    if t["status"] == "selesai":
        print(f"ERROR: {t['id']} sudah selesai.")
        return 1
    t["status"] = "selesai"
    t["hasil"] = args.hasil or ""
    t["selesai_pada"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    simpan(data)
    print(f"OK: {t['id']} selesai ✅")
    return 0


def cmd_audit(args):
    """Vonis audit Saka: lulus (tetap selesai) atau gagal (dibuka lagi)."""
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    if t["status"] != "selesai":
        print(f"ERROR: hanya tugas 'selesai' yang bisa diaudit "
              f"({t['id']} masih '{t['status']}').")
        return 1
    vonis = args.vonis
    t.setdefault("audit", []).append({
        "oleh": args.oleh,
        "vonis": vonis,
        "catatan": args.catatan or "",
        "pada": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    if vonis == "gagal":
        t["status"] = "jalan"  # dibuka lagi untuk diperbaiki
        note = f"[AUDIT {args.oleh.upper()} — GAGAL] {args.catatan or ''}".strip()
        t["detail"] = (t["detail"] + "\n" + note).strip() if t["detail"] else note
        simpan(data)
        print(f"VONIS: {t['id']} GAGAL ❌ — tugas dibuka lagi untuk {t['untuk']}.")
        print(f"Perbaiki: {args.catatan or '(tanpa catatan)'}")
        # pelajaran otomatis: tim tidak mengulangi kesalahan yang sama
        try:
            from ingat import catat_memori
            catat_memori(
                "bersama",
                topik=f"Pelajaran: {t['judul'][:60]}",
                isi=(f"Audit GAGAL oleh {args.oleh} pada {t['id']} "
                     f"({t['untuk']}): {args.catatan or '(tanpa catatan)'}. "
                     f"Jangan ulangi pola ini."),
                jenis="pelajaran")
            print("📝 Pelajaran dicatat ke memori tim.")
        except Exception as e:  # memori gagal ≠ audit gagal
            print(f"(catatan: pelajaran tak tersimpan: {e})")
    else:
        simpan(data)
        print(f"VONIS: {t['id']} LULUS ✅")
        if args.catatan:
            print(f"Catatan: {args.catatan}")
    return 0


def cmd_status(args):
    data = baca()
    print("=== Status Tim hplus ===")
    for agen in ["nara", "koda", "vera", "raka", "tara", "saka", "ari"]:
        milik = [t for t in data["tugas"] if t["untuk"] == agen]
        antri = sum(1 for t in milik if t["status"] == "antri")
        jalan = sum(1 for t in milik if t["status"] == "jalan")
        done = sum(1 for t in milik if t["status"] == "selesai")
        sibuk = "🔨 SIBUK" if jalan else ("⏳ ada antrean" if antri else "💤 idle")
        print(f"  {agen:5s}: {sibuk}  (antri {antri} | jalan {jalan} | selesai {done})")
    total_antri = sum(1 for t in data["tugas"] if t["status"] == "antri")
    total_jalan = sum(1 for t in data["tugas"] if t["status"] == "jalan")
    print(f"Total: {total_antri} antri, {total_jalan} berjalan")
    return 0


def cmd_tunda(args):
    """Tunda tugas yang berjalan (jalan -> antri) untuk interupsi prioritas."""
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    if t["status"] != "jalan":
        print(f"ERROR: hanya tugas 'jalan' yang bisa ditunda "
              f"({t['id']} masih '{t['status']}').")
        return 1
    t["status"] = "antri"
    note = f"[DITUNDA {datetime.now().strftime('%Y-%m-%d %H:%M')}] {args.alasan or ''}".strip()
    t["detail"] = (t["detail"] + "\n" + note).strip() if t["detail"] else note
    simpan(data)
    print(f"OK: {t['id']} ditunda → kembali antre ⏳")
    if args.alasan:
        print(f"Alasan: {args.alasan}")
    return 0


def cmd_ubah_prioritas(args):
    if args.prioritas not in PRIORITAS_VALID:
        print(f"ERROR: prioritas tidak valid: {args.prioritas}")
        return 1
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    lama = t["prioritas"]
    t["prioritas"] = args.prioritas
    simpan(data)
    print(f"OK: {t['id']} prioritas {lama} → {args.prioritas}")
    return 0


def cmd_minta(args):
    """Agen meminta bantuan (ke user atau agen lain). Tugas dijeda sampai 'beri'."""
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    ke = args.ke.lower()
    valid = ["user", "nara", "koda", "vera", "raka", "tara", "saka", "ari"]
    if ke not in valid:
        print(f"ERROR: tujuan tidak dikenal: {args.ke} (user/nara/koda/vera/raka/tara/saka/ari)")
        return 1
    t["minta_bantuan"] = {"ke": ke, "pesan": args.pesan,
                          "pada": datetime.now().strftime("%Y-%m-%d %H:%M")}
    simpan(data)
    siapa = "USER 🙋" if ke == "user" else ke
    print(f"OK: {t['id']} meminta bantuan ke {siapa}")
    print(f"Pesan: {args.pesan}")
    print("Tugas dijeda — jangan jalan sendiri sampai 'beri' dijalankan.")
    return 0


def cmd_beri(args):
    """Komandan memberikan bantuan yang diminta; tugas lanjut jalan."""
    data = muat()
    t = cari(data, args.id)
    if not t:
        print(f"ERROR: tugas {args.id.upper()} tidak ada")
        return 1
    if not t.get("minta_bantuan"):
        print(f"ERROR: {t['id']} tidak sedang meminta bantuan.")
        return 1
    ke = t["minta_bantuan"]["ke"]
    t["minta_bantuan"] = None
    note = (f"[BANTUAN DITERIMA {datetime.now().strftime('%Y-%m-%d %H:%M')}] "
            f"dari {ke}: {args.isi}")
    t["detail"] = (t["detail"] + "\n" + note).strip() if t["detail"] else note
    simpan(data)
    print(f"OK: {t['id']} lanjut jalan ▶️ (bantuan dari {ke} diterima)")
    return 0


def cmd_butuh(args):
    """Daftar permintaan bantuan yang menggantung + tandai yang terlambat."""
    data = baca()
    sekarang = datetime.now()
    ada = False
    for t in data["tugas"]:
        mb = t.get("minta_bantuan")
        if not mb:
            continue
        ada = True
        try:
            pada = datetime.strptime(mb["pada"], "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pada = sekarang
        jam = (sekarang - pada).total_seconds() / 3600
        flag = " ⚠️ TERLAMBAT" if jam > args.batas_jam else ""
        print(f"🙋 {t['id']} ({t['untuk']}) menunggu {mb['ke']} "
              f"selama {jam:.1f} jam{flag}")
        print(f"    pesan: {mb['pesan'][:160]}")
    if not ada:
        print("(tidak ada permintaan bantuan yang menggantung)")
    else:
        print(f"\nBatas: {args.batas_jam} jam. Komandan: ingatkan user/agen "
              f"yang TERLAMBAT, atau 'beri' jawabannya.")
    return 0


def cmd_laporan_kinerja(args):
    """Rapor kinerja tiap agen: volume, kelulusan audit, pelanggaran."""
    data = baca()
    agens = [args.agen] if args.agen else ["nara", "koda", "vera", "raka", "tara", "saka", "ari"]
    print("=== Laporan Kinerja Tim hplus ===")
    for agen in agens:
        milik = [t for t in data["tugas"] if t["untuk"] == agen]
        audits = [a for t in milik for a in t.get("audit", [])]
        lulus = sum(1 for a in audits if a["vonis"] == "lulus")
        gagal = sum(1 for a in audits if a["vonis"] == "gagal")
        total = len(milik)
        done = sum(1 for t in milik if t["status"] == "selesai")
        tingkat = f"{lulus}/{lulus + gagal} ({100 * lulus // (lulus + gagal)}%)" if audits else "-"
        print(f"\n{agen}: {total} tugas (selesai {done}) | "
              f"audit lulus {lulus}, gagal {gagal} → {tingkat}")
        for t in milik:
            for a in t.get("audit", []):
                if a["vonis"] == "gagal":
                    print(f"  ❌ {t['id']}: {a['catatan'][:100]}")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="tim.py",
        description="Papan tugas tim hplus: tambah, daftar, ambil, selesai, status.")
    sub = p.add_subparsers(dest="aksi", required=True)

    s = sub.add_parser("tambah", help="Tambah tugas baru")
    s.add_argument("judul", help="Judul tugas")
    s.add_argument("--untuk", required=True,
                   help="Agen pemilik: nara/koda/vera/raka/tara")
    s.add_argument("--prioritas", default="sedang",
                   help="rendah/sedang/tinggi/mendesak")
    s.add_argument("--detail", help="Detail/cara mengerjakan")
    s.set_defaults(func=cmd_tambah)

    s = sub.add_parser("daftar", help="Daftar tugas")
    s.add_argument("--status", choices=sorted(STATUS_VALID))
    s.add_argument("--untuk", help="Filter agen")
    s.add_argument("--detail", action="store_true")
    s.set_defaults(func=cmd_daftar)

    s = sub.add_parser("ambil", help="Ambil tugas (antri -> jalan)")
    s.add_argument("id", help="ID tugas, mis. T-001")
    s.add_argument("--oleh", required=True, help="Agen pengambil")
    s.set_defaults(func=cmd_ambil)

    s = sub.add_parser("selesai", help="Tandai tugas selesai")
    s.add_argument("id", help="ID tugas")
    s.add_argument("--hasil", help="Ringkasan hasil")
    s.set_defaults(func=cmd_selesai)

    s = sub.add_parser("audit", help="Vonis audit Saka (lulus/gagal)")
    s.add_argument("id", help="ID tugas (harus sudah selesai)")
    s.add_argument("--vonis", required=True, choices=["lulus", "gagal"],
                   help="Vonis audit")
    s.add_argument("--catatan", help="Temuan / instruksi perbaikan wajib")
    s.add_argument("--oleh", default="saka", help="Auditor (default: saka)")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("status", help="Ringkasan kesibukan tiap agen")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("tunda", help="Tunda tugas berjalan (jalan -> antri)")
    s.add_argument("id", help="ID tugas")
    s.add_argument("--alasan", help="Alasan penundaan")
    s.set_defaults(func=cmd_tunda)

    s = sub.add_parser("ubah-prioritas", help="Ubah prioritas tugas")
    s.add_argument("id", help="ID tugas")
    s.add_argument("--prioritas", required=True,
                   help="rendah/sedang/tinggi/mendesak")
    s.set_defaults(func=cmd_ubah_prioritas)

    s = sub.add_parser("butuh", help="Permintaan bantuan yang menggantung")
    s.add_argument("--batas-jam", type=float, default=2,
                   help="Batas menunggu sebelum TERLAMBAT (default 2 jam)")
    s.set_defaults(func=cmd_butuh)

    s = sub.add_parser("laporan-kinerja", help="Rapor kinerja tiap agen")
    s.add_argument("--agen", help="Filter satu agen")
    s.set_defaults(func=cmd_laporan_kinerja)

    s = sub.add_parser("minta", help="Minta bantuan (ke user/agen lain)")
    s.add_argument("id", help="ID tugas")
    s.add_argument("--ke", required=True,
                   help="user/nara/koda/vera/raka/tara/saka/ari")
    s.add_argument("--pesan", required=True, help="Apa yang dibutuhkan")
    s.set_defaults(func=cmd_minta)

    s = sub.add_parser("beri", help="Beri bantuan yang diminta; tugas lanjut")
    s.add_argument("id", help="ID tugas")
    s.add_argument("--isi", required=True, help="Jawaban/bantuan")
    s.set_defaults(func=cmd_beri)

    args = p.parse_args()
    try:
        return args.func(args)
    finally:
        lepas()  # jangan pernah bocorkan kunci, bahkan saat error


if __name__ == "__main__":
    sys.exit(main())
