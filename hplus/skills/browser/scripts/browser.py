#!/usr/bin/env python3
"""
browser.py — operasi browser seperti manusia (Playwright + Chromium).

Sesi persisten: profil di ~/.hermes-browser/ sehingga cookie & login
tetap ada antar perintah. Browser headless (cocok VPS); --tampil untuk GUI.

Contoh:
  python3 browser.py periksa
  python3 browser.py install            # BUTUH IZIN SAKA (lihat SKILL.md)
  python3 browser.py buka https://example.com
  python3 browser.py isi "#email" "nama@email.com"
  python3 browser.py klik "#daftar"
  python3 browser.py baca
  python3 browser.py screenshot bukti.png
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

PROFIL = os.path.expanduser("~/.hermes-browser")
STATE = os.path.join(PROFIL, "sesi.json")  # url terakhir
DAEMON_URL = "http://127.0.0.1:18746"
DAEMON_PID = os.path.join(PROFIL, "daemon.pid")


# ---------- klien daemon ----------
def daemon_hidup():
    try:
        with urllib.request.urlopen(DAEMON_URL + "/status", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def via_daemon(aksi, params=None):
    """Kirim aksi ke daemon bila hidup; kembalikan dict atau None."""
    if not daemon_hidup():
        return None
    data = {"aksi": aksi}
    data.update(params or {})
    req = urllib.request.Request(
        DAEMON_URL + "/aksi", data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except Exception as e:
        print(f"WARNING: daemon tidak merespons ({e}) — pakai mode sekali-jalan.")
        return None


def cmd_daemon(args):
    aksi = args.daemon_aksi
    if aksi == "status":
        print("daemon: HIDUP 🟢" if daemon_hidup() else "daemon: MATI ⚪")
        return 0
    if aksi == "start":
        if daemon_hidup():
            print("daemon sudah hidup 🟢")
            return 0
        if not playwright_ada():
            print("ERROR: playwright belum terinstal — 'install' dulu (butuh izin Saka).")
            return 1
        dpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "daemon.py")
        log = open(os.path.join(PROFIL, "daemon.log"), "a")
        subprocess.Popen([sys.executable, dpath], start_new_session=True,
                         stdout=log, stderr=log)
        import time
        for _ in range(20):
            if daemon_hidup():
                print("OK: daemon hidup 🟢 — sesi browser siap dipakai bersama.")
                return 0
            time.sleep(0.5)
        print("ERROR: daemon gagal start — cek ~/.hermes-browser/daemon.log")
        return 1
    if aksi == "stop":
        try:
            req = urllib.request.Request(DAEMON_URL + "/berhenti", data=b"{}",
                                         method="POST")
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass
        if os.path.isfile(DAEMON_PID):
            try:
                os.remove(DAEMON_PID)
            except OSError:
                pass
        print("OK: daemon dihentikan ⚪")
        return 0


def playwright_ada():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def chromium_ada():
    if not playwright_ada():
        return False
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
        capture_output=True, text=True)
    # --dry-run tidak didukung versi lama; fallback: cek folder browser
    ms = os.path.expanduser("~/.cache/ms-playwright")
    return os.path.isdir(ms) and any("chromium" in d for d in os.listdir(ms))


def cmd_periksa(_):
    pw = playwright_ada()
    cr = chromium_ada() if pw else False
    print(f"playwright: {'OK' if pw else 'BELUM'}")
    print(f"chromium  : {'OK' if cr else 'BELUM'}")
    if not (pw and cr):
        print("\nJalankan 'install' SETELAH izin Saka (lihat SKILL.md).")
        return 1
    print("\nSiap dipakai.")
    return 0


def _pip_install(paket):
    """pip install --user, dengan fallback --break-system-packages
    untuk distro modern (Debian/Ubuntu PEP 668)."""
    base = [sys.executable, "-m", "pip", "install", "--user", paket]
    for extra in ([], ["--break-system-packages"]):
        r = subprocess.run(base + extra, capture_output=True, text=True)
        if r.returncode == 0:
            return True
        if "externally-managed-environment" not in (r.stdout + r.stderr):
            print((r.stderr or r.stdout)[-800:])
            return False
    print("ERROR: pip install gagal bahkan dengan --break-system-packages")
    return False


def cmd_install(_):
    print("PROTOKOL: pastikan izin Saka sudah tercatat di papan tugas")
    print("(tugas 'Izin install' -> audit vonis lulus) sebelum lanjut.\n")
    print("[1/2] pip install playwright ...")
    if not _pip_install("playwright"):
        print("ERROR: pip install gagal")
        return 1
    print("[2/2] playwright install chromium ...")
    r = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    if r.returncode != 0:
        print("ERROR: install chromium gagal")
        return 1
    print("\nOK: browser siap. Catat instalasi di pengetahuan/<agen>/instalasi.md")
    return 0


def _butuh():
    if not (playwright_ada() and chromium_ada()):
        print("ERROR: playwright/chromium belum terinstal.")
        print("Jalankan 'periksa', lalu 'install' setelah izin Saka.")
        sys.exit(2)


def _buka_konteks(tampil=False):
    from playwright.sync_api import sync_playwright
    os.makedirs(PROFIL, exist_ok=True)
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        PROFIL, headless=not tampil,
        args=["--no-sandbox"] if os.geteuid() == 0 else [])
    return pw, ctx


def _simpan_url(url):
    os.makedirs(PROFIL, exist_ok=True)
    with open(STATE, "w") as f:
        json.dump({"url": url}, f)


def cmd_buka(args):
    r = via_daemon("buka", {"url": args.url})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        if r.get("judul"):
            print(f"Judul: {r['judul']}")
        return 0
    _butuh()
    pw, ctx = _buka_konteks(tampil=args.tampil)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    _simpan_url(page.url)
    print(f"OK: dibuka {page.url}")
    print(f"Judul: {page.title()}")
    ctx.close()
    pw.stop()
    return 0


def _dengan_halaman():
    """Buka konteks persisten dan kembali ke url terakhir."""
    from playwright.sync_api import sync_playwright
    _butuh()
    pw, ctx = _buka_konteks()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    if os.path.exists(STATE):
        url = json.load(open(STATE)).get("url")
        if url and page.url != url:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return pw, ctx, page


def _selesai(pw, ctx, page):
    _simpan_url(page.url)
    ctx.close()
    pw.stop()


def cmd_baca(_):
    r = via_daemon("baca")
    if r:
        print(r.get("teks", ""))
        if r.get("total", 0) > 4000:
            print(f"\n... (dipotong, total {r['total']} karakter)")
        return 0
    pw, ctx, page = _dengan_halaman()
    teks = page.inner_text("body")
    print(teks[:4000])
    if len(teks) > 4000:
        print(f"\n... (dipotong, total {len(teks)} karakter)")
    _selesai(pw, ctx, page)
    return 0


def cmd_judul(_):
    r = via_daemon("judul")
    if r:
        print(r.get("judul"))
        return 0
    pw, ctx, page = _dengan_halaman()
    print(page.title())
    _selesai(pw, ctx, page)
    return 0


def cmd_url(_):
    r = via_daemon("judul")
    if r:
        print(r.get("url"))
        return 0
    pw, ctx, page = _dengan_halaman()
    print(page.url)
    _selesai(pw, ctx, page)
    return 0


def cmd_klik(args):
    r = via_daemon("klik", {"selector": args.selector})
    if r:
        print(f"OK (daemon): {r.get('pesan')} -> {r.get('url')}")
        return 0
    pw, ctx, page = _dengan_halaman()
    page.click(args.selector, timeout=15000)
    page.wait_for_timeout(1500)
    _simpan_url(page.url)
    print(f"OK: klik {args.selector} -> {page.url}")
    ctx.close()
    pw.stop()
    return 0


def cmd_isi(args):
    r = via_daemon("isi", {"selector": args.selector, "teks": args.teks})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    pw, ctx, page = _dengan_halaman()
    page.fill(args.selector, args.teks, timeout=15000)
    _simpan_url(page.url)
    print(f"OK: isi {args.selector}")
    ctx.close()
    pw.stop()
    return 0


def cmd_pilih(args):
    r = via_daemon("pilih", {"selector": args.selector, "label": args.label})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    pw, ctx, page = _dengan_halaman()
    page.select_option(args.selector, label=args.label, timeout=15000)
    _simpan_url(page.url)
    print(f"OK: pilih '{args.label}' di {args.selector}")
    ctx.close()
    pw.stop()
    return 0


def cmd_tunggu(args):
    r = via_daemon("tunggu", {"target": args.target})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    import time
    pw, ctx, page = _dengan_halaman()
    target = args.target
    try:
        detik = float(target)
        time.sleep(detik)
        print(f"OK: tunggu {detik} detik")
    except ValueError:
        page.wait_for_selector(target, timeout=30000)
        print(f"OK: {target} muncul")
    _selesai(pw, ctx, page)
    return 0


def cmd_screenshot(args):
    r = via_daemon("layar", {"file": args.file})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    pw, ctx, page = _dengan_halaman()
    page.screenshot(path=args.file, full_page=args.penuh)
    print(f"OK: screenshot -> {args.file}")
    _selesai(pw, ctx, page)
    return 0


def cmd_tutup(_):
    # konteks persisten tidak butuh ditutup manual; sesi tersimpan otomatis
    print("OK: sesi tersimpan di ~/.hermes-browser/ (persisten)")
    return 0


def cmd_klik_xy(args):
    """Klik pada koordinat fraksi layar (0..1) — untuk kendali user via web."""
    r = via_daemon("klik_xy", {"x": args.x, "y": args.y})
    if r:
        print(f"OK (daemon): {r.get('pesan')} -> {r.get('url')}")
        return 0
    print("ERROR: butuh daemon hidup — 'browser.py daemon start' dulu.")
    return 1


def cmd_ketik(args):
    """Ketik teks pada elemen yang sedang fokus — via daemon."""
    r = via_daemon("ketik", {"teks": args.teks})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    print("ERROR: butuh daemon hidup — 'browser.py daemon start' dulu.")
    return 1


def cmd_tombol(args):
    """Tekan tombol keyboard (Enter/Tab/Escape/dll) — via daemon."""
    r = via_daemon("tombol", {"tombol": args.tombol})
    if r:
        print(f"OK (daemon): {r.get('pesan')}")
        return 0
    print("ERROR: butuh daemon hidup — 'browser.py daemon start' dulu.")
    return 1


def main():
    ap = argparse.ArgumentParser(description="Browser seperti manusia (Raka)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("periksa", help="Cek playwright+chromium")
    s.set_defaults(func=cmd_periksa)
    s = sub.add_parser("install", help="Install playwright+chromium (butuh izin Saka)")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("buka", help="Buka URL")
    s.add_argument("url")
    s.add_argument("--tampil", action="store_true")
    s.set_defaults(func=cmd_buka)
    s = sub.add_parser("baca", help="Baca teks halaman")
    s.set_defaults(func=cmd_baca)
    s = sub.add_parser("judul", help="Judul halaman")
    s.set_defaults(func=cmd_judul)
    s = sub.add_parser("url", help="URL saat ini")
    s.set_defaults(func=cmd_url)
    s = sub.add_parser("klik", help="Klik selector CSS")
    s.add_argument("selector")
    s.set_defaults(func=cmd_klik)
    s = sub.add_parser("isi", help="Isi field teks")
    s.add_argument("selector")
    s.add_argument("teks")
    s.set_defaults(func=cmd_isi)
    s = sub.add_parser("pilih", help="Pilih option dropdown (by label)")
    s.add_argument("selector")
    s.add_argument("label")
    s.set_defaults(func=cmd_pilih)
    s = sub.add_parser("tunggu", help="Tunggu N detik atau selector muncul")
    s.add_argument("target")
    s.set_defaults(func=cmd_tunggu)
    s = sub.add_parser("screenshot", help="Simpan screenshot")
    s.add_argument("file")
    s.add_argument("--penuh", action="store_true")
    s.set_defaults(func=cmd_screenshot)
    s = sub.add_parser("tutup", help="Tutup sesi (data tersimpan)")
    s.set_defaults(func=cmd_tutup)

    s = sub.add_parser("daemon", help="Sesi browser hidup (start/stop/status)")
    s.add_argument("daemon_aksi", choices=["start", "stop", "status"])
    s.set_defaults(func=cmd_daemon)

    s = sub.add_parser("klik-xy", help="Klik koordinat fraksi 0..1 (via daemon)")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.set_defaults(func=cmd_klik_xy)

    s = sub.add_parser("ketik", help="Ketik pada fokus (via daemon)")
    s.add_argument("teks")
    s.set_defaults(func=cmd_ketik)

    s = sub.add_parser("tombol", help="Tekan tombol keyboard (via daemon)")
    s.add_argument("tombol", help="Enter/Tab/Escape/dll")
    s.set_defaults(func=cmd_tombol)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
