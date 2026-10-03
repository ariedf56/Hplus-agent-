#!/usr/bin/env python3
"""
daemon.py — sesi browser Raka yang HIDUP (Playwright persistent).

Berjalan sebagai proses latar, melayani HTTP di 127.0.0.1:18746.
Satu halaman browser tetap terbuka (tanpa reload antar perintah),
sehingga Raka DAN user bisa mengoperasikannya bergantian —
"browser di dalam browser" via dashboard Kantor hplus.

Dikelola lewat:  browser.py daemon start|stop|status
Berhenti otomatis bila menganggur 30 menit.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 18746
PROFIL = os.path.expanduser("~/.hermes-browser")
PIDFILE = os.path.join(PROFIL, "daemon.pid")
IDLE_TIMEOUT = 1800  # detik

pw = None
ctx = None
page = None
terakhir_aktif = time.time()


def sentuh():
    global terakhir_aktif
    terakhir_aktif = time.time()


def eksekusi(aksi, p):
    """Jalankan aksi pada halaman hidup. Kembalikan dict hasil."""
    global page
    sentuh()
    if aksi == "buka":
        page.goto(p["url"], wait_until="domcontentloaded", timeout=30000)
        return {"pesan": f"dibuka {page.url}", "url": page.url,
                "judul": page.title()}
    if aksi == "klik":
        page.click(p["selector"], timeout=15000)
        page.wait_for_timeout(1200)
        return {"pesan": f"klik {p['selector']}", "url": page.url}
    if aksi == "klik_xy":
        vp = page.viewport_size or {"width": 1280, "height": 720}
        x = float(p["x"]) * vp["width"]
        y = float(p["y"]) * vp["height"]
        page.mouse.click(x, y)
        page.wait_for_timeout(1200)
        return {"pesan": f"klik ({x:.0f},{y:.0f})", "url": page.url}
    if aksi == "isi":
        page.fill(p["selector"], p["teks"], timeout=15000)
        return {"pesan": f"isi {p['selector']}", "url": page.url}
    if aksi == "ketik":
        page.keyboard.type(p["teks"])
        return {"pesan": f"diketik {len(p['teks'])} karakter", "url": page.url}
    if aksi == "tombol":
        page.keyboard.press(p["tombol"])
        page.wait_for_timeout(800)
        return {"pesan": f"tombol {p['tombol']}", "url": page.url}
    if aksi == "pilih":
        page.select_option(p["selector"], label=p["label"], timeout=15000)
        return {"pesan": f"pilih '{p['label']}'", "url": page.url}
    if aksi == "baca":
        teks = page.inner_text("body")
        return {"teks": teks[:4000], "total": len(teks), "url": page.url}
    if aksi == "judul":
        return {"judul": page.title(), "url": page.url}
    if aksi == "tunggu":
        try:
            detik = float(p["target"])
            time.sleep(detik)
            return {"pesan": f"tunggu {detik} dtk", "url": page.url}
        except ValueError:
            page.wait_for_selector(p["target"], timeout=30000)
            return {"pesan": f"{p['target']} muncul", "url": page.url}
    if aksi == "layar":
        path = p.get("file") or os.path.join(PROFIL, "layar.png")
        page.screenshot(path=path)
        return {"pesan": f"screenshot -> {path}", "file": path,
                "url": page.url}
    return {"error": f"aksi tidak dikenal: {aksi}"}


class H(BaseHTTPRequestHandler):
    server_version = "RakaBrowser/1.0"

    def _json(self, obj, kode=200):
        badan = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(kode)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)

    def _badan(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except (json.JSONDecodeError, ValueError):
            return {}

    def do_GET(self):
        sentuh()
        if self.path == "/status":
            vp = page.viewport_size if page else None
            return self._json({"jalan": True,
                               "url": page.url if page else None,
                               "viewport": vp})
        if self.path == "/layar":
            shot = page.screenshot()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(shot)))
            self.end_headers()
            self.wfile.write(shot)
            return
        self._json({"error": "tidak dikenal"}, 404)

    def do_POST(self):
        if self.path == "/aksi":
            body = self._badan()
            try:
                hasil = eksekusi(body.get("aksi"), body)
                return self._json(hasil)
            except Exception as e:  # noqa: BLE001 — terus hidup
                return self._json({"error": str(e)[:300]}, 500)
        if self.path == "/berhenti":
            self._json({"pesan": "daemon berhenti"})
            threading.Thread(target=self.server.shutdown,
                             daemon=True).start()
            return
        self._json({"error": "tidak dikenal"}, 404)

    def log_message(self, fmt, *a):
        sys.stderr.write(f"[daemon {time.strftime('%H:%M:%S')}] {fmt % a}\n")


def pengawas_menganggur():
    while True:
        time.sleep(60)
        if time.time() - terakhir_aktif > IDLE_TIMEOUT:
            sys.stderr.write("[daemon] menganggur 30 mnt → berhenti.\n")
            os._exit(0)


def layani():
    global pw, ctx, page
    from playwright.sync_api import sync_playwright
    os.makedirs(PROFIL, exist_ok=True)
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        PROFIL, headless=True, viewport={"width": 1280, "height": 720})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    threading.Thread(target=pengawas_menganggur, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    sys.stderr.write(f"[daemon] sesi browser hidup di 127.0.0.1:{PORT}\n")
    try:
        srv.serve_forever()
    finally:
        ctx.close()
        pw.stop()


def main():
    os.makedirs(PROFIL, exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        layani()
    finally:
        if os.path.isfile(PIDFILE):
            os.remove(PIDFILE)


if __name__ == "__main__":
    main()
