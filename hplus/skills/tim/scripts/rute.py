#!/usr/bin/env python3
"""
rute.py — router perintah user ke agen yang tepat.

User bicara bebas (bahkan langsung menyapa agen: "koda, buatkan bot"),
script ini menentukan agen yang paling cocok lalu MEMBANGUN panggilan
delegate_task siap eksekusi — dengan perintah MENTAH user diteruskan ke
agen, sehingga tiap agen MANDIRI menerjemahkannya via section
"Menerjemahkan perintah user" di file perannya.

Contoh:
  python3 scripts/rute.py "koda, buatkan bot telegram"
  python3 scripts/rute.py "riset dokumentasi python-telegram-bot"
  python3 scripts/rute.py "buatkan bot dan riset API-nya"   # batch
  python3 scripts/rute.py "halo apa kabar"                  # komandan

Rute bisa digabung papan tugas:
  python3 scripts/rute.py "kerjakan T-002"
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from delegasikan import susun, kode_single, kode_batch, muat_agen, AGEN_DIR

# Kata kunci per agen: (kata, bobot)
KUNCI = {
    "koda": [("buatkan", 3), ("bikin", 3), ("tulis", 2), ("kode", 3),
             ("code", 3), ("script", 3), ("program", 3), ("perbaiki", 3),
             ("fix", 3), ("bug", 3), ("debug", 3), ("refactor", 3),
             ("error", 2), ("fungsi", 2), ("aplikasi", 2)],
    "vera": [("test", 3), ("uji", 3), ("tes", 3), ("verifikasi", 3),
             ("review kode", 4), ("cek kode", 3), ("lolos", 2),
             ("berhasil jalan", 3), ("bug", 3), ("temukan bug", 4)],
    "raka": [("riset", 4), ("cari", 2), ("dokumentasi", 3), ("artikel", 2),
             ("berita", 2), ("baca tentang", 3), ("apa itu", 3),
             ("bandingkan", 2), ("referensi", 2)],
    "tara": [("sinyal", 4), ("analisa", 3), ("analisis", 3), ("harga", 2),
             ("trading", 3), ("btc", 3), ("bitcoin", 3), ("xau", 3),
             ("emas", 3), ("pasar", 2), ("profit", 2), ("chart", 2),
             ("eth", 3)],
    "nara": [("rencana", 4), ("rencanakan", 4), ("pecah", 3), ("breakdown", 3),
             ("desain", 3), ("arsitek", 3), ("langkah-langkah", 3),
             ("strategi kerja", 3)],
    "saka": [("audit", 5), ("periksa kerja", 4), ("qc", 4),
             ("nilai kerja", 4), ("quality", 3)],
    "ari": [("login", 4), ("akun", 3), ("kredensial", 4), ("credential", 4),
            ("password", 4), ("kata sandi", 4), ("api key", 3),
            ("token", 2), ("masuk akun", 4), ("daftar akun", 2),
            ("simpan password", 4)],
}

AMBANG_BATCH = 4   # skor minimum agar ikut batch multi-agen
AMBANG_TUNGGAL = 2  # skor minimum agar dirute ke agen (bukan komandan)


def skor_rute(teks):
    """Kembalikan [(agen, skor)] terurut.
    1. Vokatif eksplisit ("koda, ...", "@koda", "tolong koda") → langsung.
    2. Sebutan nama biasa ("kerja koda") hanya bobot kecil — maksud
       kalimat (kata kunci kuat seperti "audit") tetap menang.
    3. Disambiguasi "audit": "audit" + konteks kode (bug/kode/program/...)
       tanpa kata "kerja"/"tugas" = audit TEKNIS kode → Vera.
       Saka mengaudit pekerjaan agen, bukan kode.
    """
    t = teks.lower()
    for f in os.listdir(AGEN_DIR):
        if f.endswith(".json"):
            nama = f[:-5]
            if (re.search(rf"@{nama}\b", t)
                    or re.search(rf"^{nama}\s*[,.:!]", t)
                    or re.search(rf"\b(tolong|minta|suruh|panggil)\s+{nama}\b", t)):
                return [(nama, 99)]
    kode_ctx = any(re.search(rf"\b{re.escape(w)}\b", t)
                   for w in ["bug", "kode", "code", "coding", "codingan",
                             "kodingan", "program", "fungsi", "error", "script"])
    audit_agen = "audit" in t and "kerja" not in t and "tugas" not in t
    audit_kode = audit_agen and kode_ctx
    # Saat maksudnya INSPEKSI kode (audit/cek/temukan), kata-kata kode yang
    # netral tidak boleh menyeret Koda ikut (mencegah ubahan tak diminta).
    # Koda hanya ikut bila ada kata kerja aksi (perbaiki/buat/tulis/dll).
    KODE_NETRAL = {"bug", "kode", "code", "coding", "codingan", "kodingan",
                   "program", "fungsi", "error", "script", "aplikasi"}
    hasil = {}
    for agen, katakunci in KUNCI.items():
        skor = 0
        for kata, bobot in katakunci:
            if agen == "saka" and kata == "audit" and audit_kode:
                continue  # audit kode = ranah Vera
            if agen == "koda" and kata in KODE_NETRAL and audit_kode:
                continue  # inspeksi kode: Koda hanya ikut bila ada kata kerja aksi
            if " " in kata:
                if kata in t:
                    skor += bobot
            elif re.search(rf"\b{re.escape(kata)}\b", t):
                skor += bobot
        if agen == "vera" and audit_kode:
            skor += 5  # "audit ... bug/kode" → audit teknis kode
        if re.search(rf"\b{re.escape(agen)}\b", t):
            skor += 2  # disebut sebagai objek, bukan panggilan
        if skor:
            hasil[agen] = skor
    return sorted(hasil.items(), key=lambda x: -x[1])


def main():
    p = argparse.ArgumentParser(
        prog="rute.py",
        description="Rutekan perintah user ke agen yang tepat + bangun delegate_task.")
    p.add_argument("perintah", help="Perintah user (tulis dalam kutip)")
    p.add_argument("--latar", action="store_true", help="background=True")
    p.add_argument("--tugas", help="Kaitkan ke ID tugas papan (mis. T-002)")
    args = p.parse_args()

    peringkat = skor_rute(args.perintah)
    if not peringkat or peringkat[0][1] < AMBANG_TUNGGAL:
        print("# RUTE: komandan (Hermes sendiri)")
        print("# Tidak ada agen yang cocok jelas — Komandan menangani")
        print("# langsung, atau pecah via Nara bila tugasnya besar.")
        print(f"# Perintah: {args.perintah}")
        return 0

    # Batch: beberapa agen skor tinggi → paralel
    kandidat = [a for a, s in peringkat if s >= AMBANG_BATCH]
    if len(kandidat) >= 2:
        daftar = [susun(a, args.tugas,
                        konteks_tambahan=f"PERINTAH USER (mentah): {args.perintah}")
                  for a in kandidat[:3]]
        print(f"# RUTE: batch paralel → {', '.join(kandidat[:3])}")
        print("# Tiap agen menerima perintah mentah user dan "
              "menerjemahkannya mandiri.\n")
        print(kode_batch(daftar, args.latar))
        return 0

    agen = peringkat[0][0]
    info = muat_agen(agen)
    s = susun(agen, args.tugas,
              konteks_tambahan=f"PERINTAH USER (mentah): {args.perintah}")
    eksplisit = " (disebut eksplisit)" if peringkat[0][1] == 99 else ""
    print(f"# RUTE: {info['tampil']}{eksplisit}")
    print("# Agen menerima perintah mentah user dan menerjemahkannya "
          "mandiri via perannya.\n")
    print(kode_single(s, args.latar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
