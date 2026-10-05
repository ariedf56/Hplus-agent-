#!/usr/bin/env python3
"""pekerja.py — pekerja latar Kantor hplus.

Menjadikan agen GUI "hidup": setiap tugas 'antri' di papan dikerjakan lewat
`hermes chat -q` (Hermes ASLI, dengan semua tool-nya), lalu ditandai selesai
beserta laporannya. GUI Kantor menampilkan semuanya live karena membaca papan
yang sama (tugas.json milik skill tim).

Dijalankan di HP Ari (Termux), BUKAN di mesin ini:
    nohup python3 ~/.hermes/skills/kantor/pekerja.py > ~/.pekerja.log 2>&1 &
Berhenti:
    pkill -f "kantor/pekerja.py"
Tes sekali jalan (ambil 1 tugas antri lalu keluar):
    python3 ~/.hermes/skills/kantor/pekerja.py --sekali

Pengaturan via environment:
    PEKERJA_POLL     jeda antar putaran detik (default 60)
    PEKERJA_TIMEOUT   batas waktu per tugas detik (default 1500 = 25 mnt)
    PEKERJA_HERMES    perintah hermes (default "hermes")
    PEKERJA_TIM       path ke tim.py (default: ../tim/scripts/tim.py)

Batas jujur:
- 1 tugas dalam satu waktu (aman, tidak paralel).
- Tugas gagal 3x -> ditunda (tunda) agar tidak mengulang selamanya.
- Butuh hermes yang sudah bisa jalan + model terkonfigurasi di HP.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

DASAR = os.path.dirname(os.path.realpath(__file__))


def cari_tim():
    """Temukan tim.py: env -> relatif skill -> ~/.hermes."""
    kandidat = [
        os.environ.get("PEKERJA_TIM", ""),
        os.path.realpath(os.path.join(DASAR, "..", "tim", "scripts", "tim.py")),
        os.path.expanduser("~/.hermes/skills/tim/scripts/tim.py"),
    ]
    for k in kandidat:
        if k and os.path.isfile(k):
            return k
    return None


def muat_tim(path_tim):
    import importlib.util
    spec = importlib.util.spec_from_file_location("tim_board", path_tim)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


POLL = int(os.environ.get("PEKERJA_POLL", "60"))
TIMEOUT = int(os.environ.get("PEKERJA_TIMEOUT", "1500"))
HERMES = os.environ.get("PEKERJA_HERMES", "hermes")
MAX_COBA = 3

PROMPT = """Kamu adalah Komandan tim hplus yang dijalankan lewat Hermes.

TUGAS (dari papan tim):
- ID: {tid}
- Judul: {judul}
- Agen pelaksana: {untuk}
- Detail: {detail}

CARA KERJA (wajib, tanpa minta konfirmasi):
1. Mulai: jalankan `python3 {timpy} ambil {tid} --oleh komandan`
2. Kerjakan isi tugas sampai tuntas. Boleh delegasikan ke subagen {untuk} via delegate_task. Skill ada di {skilldir}/.
3. Jika TERHALANG dan butuh user (OTP/CAPTCHA/login/keputusan): jalankan `python3 {timpy} minta {tid} --ke user --pesan "<pesan singkat>"` lalu BERHENTI. Jangan tandai selesai.
4. Jika selesai: `python3 {timpy} selesai {tid} --hasil "<ringkasan hasil>"`
5. Akhiri responsmu dengan blok persis seperti ini:
[LAPORAN]
<ringkasan hasil kerja, bahasa Indonesia santai>
[/LAPORAN]
"""


def log(*a):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]", *a, flush=True)


def ambil_antri(tim):
    data = tim.baca()
    antri = [t for t in data["tugas"] if t["status"] == "antri"]
    antri.sort(key=lambda t: t["id"])
    return antri[0] if antri else None


def klaim(tim, tid):
    data = tim.muat()
    t = tim.cari(data, tid)
    if not t or t["status"] != "antri":
        tim.lepas()
        return None
    t["status"] = "jalan"
    t["oleh"] = "pekerja"
    t["diambil_pada"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    t["coba"] = int(t.get("coba", 0)) + 1
    tim.simpan(data)
    return t


def selesai(tim, tid, hasil):
    data = tim.muat()
    t = tim.cari(data, tid)
    if t:
        t["status"] = "selesai"
        t["hasil"] = hasil
        t["selesai_pada"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        t.pop("diambil_pada", None)
        tim.simpan(data)
    else:
        tim.lepas()


def kembalikan(tim, tid, alasan):
    """Kembalikan ke antri (coba lagi nanti) atau tunda bila sudah 3x gagal."""
    data = tim.muat()
    t = tim.cari(data, tid)
    if t:
        if int(t.get("coba", 1)) >= MAX_COBA:
            t["status"] = "tunda"
            t["alasan_tunda"] = alasan
            log(f"{tid}: ditunda setelah {MAX_COBA}x gagal ({alasan})")
        else:
            t["status"] = "antri"
            t.pop("oleh", None)
            t.pop("diambil_pada", None)
            log(f"{tid}: kembali antri ({alasan})")
        tim.simpan(data)
    else:
        tim.lepas()


def ekstrak_laporan(stdout):
    m = re.search(r"\[LAPORAN\]\s*(.*?)\s*\[/LAPORAN\]", stdout, re.S)
    if m and m.group(1).strip():
        return m.group(1).strip()[:4000]
    return ""


def kerjakan(tim, t, path_tim):
    tid = t["id"]
    skilldir = os.path.dirname(os.path.dirname(os.path.realpath(path_tim)))
    prompt = PROMPT.format(
        tid=tid, judul=t["judul"], untuk=t.get("untuk", "-"),
        detail=t.get("detail") or "-",
        timpy=path_tim, skilldir=os.path.dirname(skilldir),
    )
    log(f"{tid}: mulai ({t['judul'][:60]})")
    try:
        r = subprocess.run(
            [HERMES, "chat", "-q", prompt],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except FileNotFoundError:
        log(f"perintah '{HERMES}' tidak ditemukan — pastikan Hermes terpasang")
        return False
    except subprocess.TimeoutExpired:
        log(f"{tid}: timeout {TIMEOUT}s")
        return False
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    if r.returncode != 0:
        log(f"{tid}: hermes exit {r.returncode}")
        log("keluaran:", out[-500:])
        return False
    # Hermes mungkin sudah menandai selesai sendiri via tim.py selesai
    data = tim.baca()
    segar = tim.cari(data, tid)
    if segar and segar["status"] == "selesai":
        log(f"{tid}: selesai oleh Hermes langsung ✅")
        return True
    if segar and segar.get("minta_bantuan"):
        log(f"{tid}: butuh bantuan user, dibiarkan 🙋")
        return True  # bukan gagal; menunggu user
    lap = ekstrak_laporan(r.stdout or "")
    if not lap:
        lap = "(Hermes selesai tanpa blok laporan)\n" + (r.stdout or "")[-1200:]
    selesai(tim, tid, lap)
    log(f"{tid}: selesai ✅")
    return True


def putaran(tim, path_tim):
    if not shutil.which(HERMES):
        log(f"'{HERMES}' tidak ada di PATH — tidur {POLL}s")
        return False
    t = ambil_antri(tim)
    if not t:
        return False
    diklaim = klaim(tim, t["id"])
    if not diklaim:
        return False
    ok = kerjakan(tim, diklaim, path_tim)
    if not ok:
        kembalikan(tim, diklaim["id"], "hermes gagal/timeout")
    return True


def main():
    sekali = "--sekali" in sys.argv
    path_tim = cari_tim()
    if not path_tim:
        print("ERROR: tim.py tidak ditemukan.", file=sys.stderr)
        sys.exit(1)
    tim = muat_tim(path_tim)
    log(f"pekerja jalan (tim: {path_tim}, poll {POLL}s)")
    if sekali:
        putaran(tim, path_tim)
        return
    while True:
        try:
            ada = putaran(tim, path_tim)
            time.sleep(5 if ada else POLL)
        except KeyboardInterrupt:
            log("berhenti.")
            break
        except Exception as e:  # noqa: BLE001 — pekerja tidak boleh mati
            log(f"galat: {e}")
            time.sleep(POLL)


if __name__ == "__main__":
    main()
