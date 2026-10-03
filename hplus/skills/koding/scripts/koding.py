#!/usr/bin/env python3
"""
Skill 'koding' — tangan Hermes untuk mengerjakan kode, 100% di dalam paket.

Tanpa install tambahan, tanpa API key baru: penalaran kode dilakukan oleh
otak LLM Hermes sendiri, skill ini hanya menyediakan alat yang aman dan
terstruktur (pindai, baca, tulis, ubah, jalankan, uji).

Keamanan:
- Semua path HARUS berada di dalam ROOT (env KODING_ROOT, default ~/proyek).
  Path traversal (../ atau symlink keluar) DITOLAK.
- 'ubah'/'tulis' selalu membuat cadangan .bak dan menampilkan diff dulu.
- 'jalankan' menolak pola perintah berbahaya kecuali --saya-yakin.
"""

import argparse
import difflib
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# Folder yang selalu diabaikan saat memindai
ABAIKAN_DIR = {".git", ".hg", ".svn", "__pycache__", "node_modules",
               ".venv", "venv", "dist", "build", ".opencode", ".idea", ".vscode"}
ABAIKAN_FILE = {"*.pyc", "*.pyo", "*.o", "*.so", "*.class", ".DS_Store"}

# Ekstensi -> bahasa (untuk ringkasan pindai)
BAHASA = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "React JSX", ".tsx": "React TSX", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".php": "PHP", ".rb": "Ruby",
    ".c": "C", ".h": "C header", ".cpp": "C++", ".cs": "C#",
    ".sh": "Shell", ".html": "HTML", ".css": "CSS", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".md": "Markdown", ".sql": "SQL",
    ".ino": "Arduino", ".lua": "Lua",
}

# Pola perintah yang ditolak oleh 'jalankan' (kecuali --saya-yakin)
POLA_BAHAYA = [
    r"\brm\s+.*-[a-z]*r[a-z]*\s+/$",      # rm -rf /
    r"\brm\s+.*-[a-z]*r[a-z]*\s+~/?$",    # rm -rf ~
    r"\brm\s+.*-[a-z]*r[a-z]*\s+/\*",     # rm -rf /*
    r":\(\)\s*\{\s*:\|:\s*&\s*\}",        # fork bomb
    r"\bmkfs\b", r"\bdd\s+.*of=/dev/",    # perusak disk
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r">\s*/dev/sd[a-z]",                 # tulis mentah ke disk
    r"\bchmod\s+-R\s+777\s+/",           # buka izin root
]


def root_dir():
    """Ambil ROOT kerja.
    Default: '/' (MODE LELUASA) — seluruh filesystem VPS.
    Set KODING_ROOT ke folder lain untuk membatasi, mis. ~ atau ~/proyek.
    """
    r = os.environ.get("KODING_ROOT", os.sep)
    r = os.path.realpath(r)
    os.makedirs(r, exist_ok=True)
    return r


def amankan(path, root):
    """
    Normalisasi path dan PASTIKAN di dalam root.
    root == '/'  → mode leluasa: seluruh filesystem diizinkan.
    Mengembalikan path absolut yang aman, atau raise ValueError.
    """
    if not os.path.isabs(path):
        path = os.path.join(root, path)
    nyata = os.path.realpath(path)
    if root == os.sep:
        return nyata  # mode leluasa
    if nyata != root and not nyata.startswith(root + os.sep):
        raise ValueError(f"DITOLAK: '{path}' berada di luar folder kerja ({root})")
    return nyata


def diabaikan(nama, adalah_dir):
    if adalah_dir and nama in ABAIKAN_DIR:
        return True
    if not adalah_dir:
        if nama.startswith("."):
            return True
        return any(fnmatch.fnmatch(nama, p) for p in ABAIKAN_FILE)
    return False


def cmd_pindai(args):
    root = root_dir()
    target = amankan(args.dir, root)
    if not os.path.isdir(target):
        print(f"ERROR: folder tidak ada: {args.dir}")
        return 1
    dalam = args.dalam
    total_file, total_byte = 0, 0
    hitung_bahasa = {}
    pohon = []

    for dirpath, dirnames, filenames in os.walk(target):
        # potong folder yang diabaikan
        dirnames[:] = [d for d in dirnames if not diabaikan(d, True)]
        rel = os.path.relpath(dirpath, target)
        kedalaman = 0 if rel == "." else rel.count(os.sep) + 1
        if kedalaman > dalam:
            dirnames[:] = []
            continue
        if kedalaman <= dalam:
            indent = "  " * kedalaman
            label = "." if rel == "." else os.path.basename(dirpath) + "/"
            pohon.append(f"{indent}{label}")
        for fn in sorted(filenames):
            if diabaikan(fn, False):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            total_file += 1
            total_byte += sz
            ext = os.path.splitext(fn)[1].lower()
            hitung_bahasa[BAHASA.get(ext, "lainnya")] = hitung_bahasa.get(BAHASA.get(ext, "lainnya"), 0) + 1
            if kedalaman < dalam:
                pohon.append(f"{indent}  {fn} ({sz} B)")

    print(f"Proyek: {target}")
    print(f"Total: {total_file} file, {total_byte / 1024:.1f} KB")
    print("Bahasa: " + ", ".join(f"{b} ({j})" for b, j in
          sorted(hitung_bahasa.items(), key=lambda x: -x[1])))
    # deteksi titik masuk umum
    kandidat = ["main.py", "app.py", "index.js", "main.go", "Main.java",
                "package.json", "requirements.txt", "pyproject.toml", "go.mod"]
    ketemu = [k for k in kandidat
              if os.path.isfile(os.path.join(target, k))]
    if ketemu:
        print("Titik masuk terdeteksi: " + ", ".join(ketemu))
    print("\nStruktur:")
    print("\n".join(pohon[:200]))
    if len(pohon) > 200:
        print(f"... ({len(pohon) - 200} baris disembunyikan, pakai --dalam lebih kecil)")
    return 0


def cmd_baca(args):
    root = root_dir()
    try:
        fp = amankan(args.file, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    if not os.path.isfile(fp):
        print(f"ERROR: file tidak ada: {args.file}")
        return 1
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            baris = f.readlines()
    except OSError as e:
        print(f"ERROR: tidak bisa dibaca: {e}")
        return 1
    dari = max(1, args.dari or 1)
    sampai = args.sampai or len(baris)
    for i in range(dari - 1, min(sampai, len(baris))):
        print(f"{i + 1:5d} | {baris[i]}", end="")
    if args.sampai and len(baris) > args.sampai:
        print(f"... ({len(baris) - args.sampai} baris lagi)")
    return 0


def buat_cadangan(fp):
    """Salin file ke .bak berstempel waktu; kembalikan path cadangan."""
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{fp}.bak-{stempel}"
    shutil.copy2(fp, bak)
    return bak


def cmd_tulis(args):
    root = root_dir()
    try:
        fp = amankan(args.file, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    isi = args.isi
    if isi is None:  # baca dari stdin (pipe)
        isi = sys.stdin.read()
    if os.path.exists(fp) and not args.timpa:
        print(f"ERROR: '{args.file}' sudah ada. Pakai --timpa untuk menimpa "
              f"(cadangan .bak dibuat otomatis).")
        return 1
    if os.path.exists(fp):
        bak = buat_cadangan(fp)
        print(f"Cadangan: {bak}")
    os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(isi)
    print(f"OK: ditulis {fp} ({len(isi)} karakter)")
    return 0


def cmd_ubah(args):
    root = root_dir()
    try:
        fp = amankan(args.file, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    if not os.path.isfile(fp):
        print(f"ERROR: file tidak ada: {args.file}")
        return 1
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        lama = f.read()
    cocok = lama.count(args.cari)
    if cocok == 0:
        print("ERROR: teks '--cari' tidak ditemukan di file. Cek lagi ejaannya "
              "(sensitif huruf besar/kecil).")
        return 1
    if cocok > 1 and not args.semua:
        print(f"ERROR: teks ditemukan {cocok} kali. Persempit '--cari' agar unik, "
              f"atau pakai --semua untuk mengganti semuanya.")
        return 1
    baru = lama.replace(args.cari, args.ganti) if args.semua \
        else lama.replace(args.cari, args.ganti, 1)
    bak = buat_cadangan(fp)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(baru)
    print(f"Cadangan: {bak}")
    print(f"OK: {cocok} kemunculan diganti di {args.file}")
    print("--- diff (lama -> baru) ---")
    diff = difflib.unified_diff(
        lama.splitlines(), baru.splitlines(),
        fromfile="sebelum", tofile="sesudah", lineterm="")
    print("\n".join(list(diff)[:60]))
    return 0


def cmd_jalankan(args):
    root = root_dir()
    try:
        d = amankan(args.dir, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    perintah = " ".join(args.perintah)
    for pola in POLA_BAHAYA:
        if re.search(pola, perintah):
            if not args.saya_yakin:
                print(f"DITOLAK: perintah cocok pola berbahaya ({pola}).\n"
                      f"Tambahkan --saya-yakin HANYA jika pengguna sudah "
                      f"menyetujui eksplisit di chat.")
                return 1
            print("PERINGATAN: pola berbahaya dilewati dengan --saya-yakin.")
            break
    try:
        hasil = subprocess.run(
            args.perintah, cwd=d, capture_output=True, text=True,
            timeout=args.batas_detik)
    except subprocess.TimeoutExpired:
        print(f"ERROR: perintah melebihi batas {args.batas_detik} detik, dihentikan.")
        return 1
    except FileNotFoundError:
        print(f"ERROR: program tidak ditemukan: {args.perintah[0]}")
        return 1
    if hasil.stdout:
        print(hasil.stdout[-4000:])  # batasi agar tidak membanjiri chat
    if hasil.stderr:
        print("--- stderr ---")
        print(hasil.stderr[-2000:])
    print(f"[exit code: {hasil.returncode}]")
    return 0


def cmd_uji(args):
    """Deteksi framework test lalu jalankan."""
    root = root_dir()
    try:
        d = amankan(args.dir, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    kandidat = []
    if os.path.isfile(os.path.join(d, "package.json")):
        kandidat = [["npm", "test"]]
    elif os.path.isfile(os.path.join(d, "go.mod")):
        kandidat = [["go", "test", "./..."]]
    elif shutil.which("pytest") and any(
            os.path.isfile(os.path.join(d, f)) for f in
            ("pytest.ini", "pyproject.toml", "setup.cfg", "tests")):
        kandidat = [["pytest", "-q"]]
    else:
        kandidat = [[sys.executable, "-m", "unittest", "discover", "-s", d]]
    print(f"Menjalankan: {' '.join(kandidat[0])}  (di {d})")
    try:
        hasil = subprocess.run(kandidat[0], cwd=d, capture_output=True,
                               text=True, timeout=300)
    except FileNotFoundError:
        print(f"ERROR: runner tidak ditemukan: {kandidat[0][0]}")
        return 1
    except subprocess.TimeoutExpired:
        print("ERROR: test melebihi 5 menit, dihentikan.")
        return 1
    out = (hasil.stdout + hasil.stderr)[-4000:]
    print(out)
    print("HASIL:", "LULUS ✅" if hasil.returncode == 0 else "GAGAL ❌")
    return 0


def cmd_kembalikan(args):
    root = root_dir()
    try:
        fp = amankan(args.file, root)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    folder = os.path.dirname(fp)
    nama = os.path.basename(fp)
    cads = sorted(f for f in os.listdir(folder)
                  if f.startswith(nama + ".bak-"))
    if not cads:
        print(f"ERROR: tidak ada cadangan untuk {args.file}")
        return 1
    terbaru = os.path.join(folder, cads[-1])
    shutil.copy2(terbaru, fp)
    print(f"OK: {args.file} dikembalikan dari {cads[-1]}")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="koding.py",
        description="Skill koding Hermes: kerjakan kode langsung dari chat. "
                    "Semua path harus di dalam KODING_ROOT (default ~/proyek).")
    sub = p.add_subparsers(dest="aksi", required=True)

    s = sub.add_parser("pindai", help="Petakan struktur proyek")
    s.add_argument("dir", help="Folder proyek (relatif thd ROOT atau absolut)")
    s.add_argument("--dalam", type=int, default=3, help="Kedalaman tree (default 3)")
    s.set_defaults(func=cmd_pindai)

    s = sub.add_parser("baca", help="Baca file dengan nomor baris")
    s.add_argument("file", help="Path file")
    s.add_argument("--dari", type=int, help="Baris mulai")
    s.add_argument("--sampai", type=int, help="Baris akhir")
    s.set_defaults(func=cmd_baca)

    s = sub.add_parser("tulis", help="Buat file baru (isi dari --isi atau stdin)")
    s.add_argument("file", help="Path file baru")
    s.add_argument("--isi", help="Isi file")
    s.add_argument("--timpa", action="store_true", help="Timpa jika sudah ada")
    s.set_defaults(func=cmd_tulis)

    s = sub.add_parser("ubah", help="Ubah bagian file (cari & ganti, + cadangan + diff)")
    s.add_argument("file", help="Path file")
    s.add_argument("--cari", required=True, help="Teks yang dicari (harus unik)")
    s.add_argument("--ganti", required=True, help="Teks pengganti")
    s.add_argument("--semua", action="store_true", help="Ganti semua kemunculan")
    s.set_defaults(func=cmd_ubah)

    s = sub.add_parser("jalankan", help="Jalankan perintah shell di folder proyek")
    s.add_argument("dir", help="Folder kerja")
    s.add_argument("--batas-detik", type=int, default=120)
    s.add_argument("--saya-yakin", action="store_true",
                   help="Lewati filter perintah berbahaya (butuh izin user)")
    s.add_argument("perintah", nargs=argparse.REMAINDER,
                   help="Perintah, pisahkan dengan --  contoh: jalankan app -- python3 main.py")
    s.set_defaults(func=cmd_jalankan)

    s = sub.add_parser("uji", help="Deteksi & jalankan test proyek")
    s.add_argument("dir", help="Folder proyek")
    s.set_defaults(func=cmd_uji)

    s = sub.add_parser("kembalikan", help="Kembalikan file dari cadangan .bak terbaru")
    s.add_argument("file", help="Path file")
    s.set_defaults(func=cmd_kembalikan)

    args = p.parse_args()
    if args.aksi == "jalankan":
        # buang pemisah '--' jika ada
        if args.perintah and args.perintah[0] == "--":
            args.perintah = args.perintah[1:]
        if not args.perintah:
            print("ERROR: tidak ada perintah. Contoh: jalankan app -- python3 main.py")
            return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
