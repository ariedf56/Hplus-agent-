#!/usr/bin/env python3
"""
server.py — Kantor hplus 🏢 (Mission Control via browser).

Dashboard live untuk tim agen: animasi kantor/rumah/kafe, buat tugas
lewat web, chat dengan tim, dan jawab permintaan bantuan agen
(OTP/CAPTCHA/dll) langsung dari browser/HP.

Jalankan:  python3 server.py [--port 8080]
Buka:      http://<ip-vps>:8080

Stdlib saja. API JSON:
  GET  /api/status          → state tiap agen (kerja/butuh/tidur/makan/ngobrol)
  GET  /api/papan           → seluruh papan tugas
  POST /api/tugas           → {judul, untuk?, prioritas?, detail?}
  POST /api/aksi            → {aksi, id, ...} (ambil/selesai/tunda/beri/minta/audit/ubah-prioritas)
  GET  /api/chat            → log chat + permintaan bantuan yg menggantung
  POST /api/chat            → {teks} kirim pesan user (dirute otomatis ke agen)
  GET  /api/agen/<nama>     → detail agen (tugas, audit, skill)
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

DASAR = os.path.dirname(os.path.realpath(__file__))
SKRIP = os.path.join(DASAR, "..", "tim", "scripts")
sys.path.insert(0, os.path.realpath(SKRIP))

import tim                      # noqa: E402
from rute import skor_rute, AMBANG_TUNGGAL, AMBANG_BATCH  # noqa: E402

CHAT = os.path.join(DASAR, "chat.json")
AGEN_ORDER = ["nara", "koda", "vera", "raka", "tara", "saka", "ari"]

# Password opsional (env KANTOR_PASSWORD atau file ~/.kantor-password dibaca
# oleh script Termux). Kalau di-set, SEMUA route wajib HTTP Basic Auth.
# WAJIB diisi sebelum link dibuka ke publik!
KANTOR_PASSWORD = os.environ.get("KANTOR_PASSWORD", "")

# --- LLM opsional: bikin agen bisa menjawab langsung di chat ---
# Isi HPLUS_LLM_KEY di Termux (export, JANGAN di chat) untuk jawaban AI penuh.
# Tanpa key: agen menjawab dari data papan (status/antrian/laporan) — tetap nyata.
LLM_KEY = os.environ.get("HPLUS_LLM_KEY", "")
LLM_MODEL = os.environ.get("HPLUS_LLM_MODEL", "gpt-4o-mini")
LLM_URL = os.environ.get("HPLUS_LLM_URL", "https://api.openai.com/v1/chat/completions")


def _sekarang():
    return datetime.now().strftime("%H:%M")


def balas_deterministik(tl, data):
    """Jawab pertanyaan seputar papan langsung dari data.
    Kembalikan (dari, teks) atau None bila tidak cocok pola."""
    tugas = data["tugas"]
    belum = [t for t in tugas if t["status"] != "selesai"]
    if any(k in tl for k in ("status tim", "siapa kerja", "siapa yang kerja",
                             "lagi ngapain", "lagi apa")):
        states = state_agen()
        kerja = [h for h in states if h["state"] == "kerja"]
        butuh = [h for h in states if h["state"] == "butuh"]
        santai = [h for h in states if h["state"] not in ("kerja", "butuh")]
        baris = []
        if kerja:
            baris.append("🔨 Kerja: " + ", ".join(h["tampil"] for h in kerja))
        if butuh:
            baris.append("🙋 Butuh bantuan: " + ", ".join(h["tampil"] for h in butuh))
        if santai:
            baris.append("💤 Santai: " + ", ".join(h["tampil"] for h in santai))
        return ("komandan", "\n".join(baris) if baris else "Tim kosong?")
    if "daftar tugas" in tl or "list tugas" in tl or tl.strip() == "tugas":
        if not belum:
            return ("komandan", "📋 Tidak ada tugas — papan bersih! 🎉")
        baris = ["📋 Daftar tugas:"]
        for t in belum[-15:]:
            info = muat_agen(t["untuk"])
            baris.append(f"{t['id']} [{t['status']}] {t['judul']} — {info['tampil']}")
        return ("komandan", "\n".join(baris))
    if "laporan" in tl:
        sdh = [t for t in tugas if t["status"] == "selesai" and t.get("hasil")]
        if not sdh:
            return ("komandan", "📣 Belum ada laporan.")
        t = sdh[-1]
        info = muat_agen(t["untuk"])
        return ("komandan",
                f"📣 Laporan terakhir ({t['id']}, {info['tampil']}):\n{t['hasil'][:400]}")
    return None


def akuisisi_agen(agen, judul):
    """Balasan agen saat menerima tugas: data antrian nyata."""
    data = tim.baca()
    n = len([t for t in data["tugas"]
             if t["untuk"] == agen and t["status"] in ("antri", "jalan")])
    return (agen, f"Siap! Saya kerjakan: {judul}\nAntrian saya sekarang {n} tugas. "
                  f"Pantau saya di kantor ya 👀")


def tanya_llm(nama, teks_pertanyaan):
    """Tanya LLM sebagai agen (persona dari peran/<nama>.md).
    Kembalikan teks jawaban atau None (tanpa key / gagal)."""
    if not LLM_KEY:
        return None
    import urllib.request
    pf = os.path.realpath(os.path.join(DASAR, "..", "tim", "peran", f"{nama}.md"))
    persona = ""
    if os.path.isfile(pf):
        with open(pf, encoding="utf-8") as f:
            persona = f.read(2000)
    info = muat_agen(nama)
    data = tim.baca()
    tugasku = [t for t in data["tugas"]
               if t["untuk"] == nama and t["status"] != "selesai"][-5]
    konteks = "\n".join(f"- {t['id']} [{t['status']}] {t['judul']}" for t in tugasku)
    system = (f"Kamu {info['tampil']}, {info['peran']} di tim hplus. "
              f"Jawab singkat (maks 3 kalimat), bahasa Indonesia santai, "
              f"sebagai dirimu.\nTugasmu saat ini:\n{konteks or '(tidak ada)'}"
              f"\n\nPeranmu:\n{persona[:1200]}")
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": teks_pertanyaan}],
        "max_tokens": 300, "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(
            LLM_URL, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {LLM_KEY}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        return d["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def muat_agen(nama):
    p = os.path.join(DASAR, "..", "tim", "agen", f"{nama}.json")
    with open(os.path.realpath(p), encoding="utf-8") as f:
        return json.load(f)


def muat_chat():
    if not os.path.isfile(CHAT):
        return []
    try:
        with open(CHAT, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def simpan_chat(log):
    tmp = CHAT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(log[-200:], f, ensure_ascii=False)
    os.replace(tmp, CHAT)


def state_agen():
    """Turunkan state live tiap agen dari papan tugas.

    Agen dengan tugas 'antri' ATAU 'jalan' dianggap BEKERJA di kantor
    (ditugaskan = sudah di meja kerja). 'antri' = menunggu dikerjakan,
    'jalan' = sedang dikerjakan.
    """
    data = tim.baca()
    tampil = {}
    hasil = []
    menganggur = []
    for nama in AGEN_ORDER:
        info = muat_agen(nama)
        tampil[nama] = info["tampil"]
        jalan = [t for t in data["tugas"]
                 if t["untuk"] == nama and t["status"] == "jalan"]
        antri = [t for t in data["tugas"]
                 if t["untuk"] == nama and t["status"] == "antri"]
        butuh = [t for t in jalan if t.get("minta_bantuan")]
        semua = jalan + antri
        tugas = jalan[0] if jalan else (semua[0] if semua else None)
        if butuh:
            st, ket = "butuh", butuh[0]
        elif semua:
            st, ket = "kerja", tugas
        else:
            st, ket = "santai", None
            menganggur.append(nama)
        hasil.append({
            "nama": nama, "tampil": info["tampil"], "avatar": info["avatar"],
            "warna": info["warna"], "peran": info["peran"],
            "state": st, "tugas": ket,
            "tugas_semua": [{"id": t["id"], "judul": t["judul"],
                             "status": t["status"]} for t in semua],
        })
    # --- ambient: yang santai disebar ke rumah/kafe (deterministik per jam)
    # ngobrol berpasangan, sisanya tidur/makan
    jam = datetime.now().strftime("%Y-%m-%d %H")
    acak = int(hashlib.md5(jam.encode()).hexdigest(), 16)
    peta = {}
    for i, nama in enumerate(menganggur):
        if i % 2 == 0 and i + 1 < len(menganggur):
            peta[nama] = ("ngobrol", menganggur[i + 1])
        else:
            peta[nama] = (["tidur", "makan"][(acak >> i) % 2], None)
    for i in range(0, len(menganggur) - 1, 2):
        peta[menganggur[i + 1]] = ("ngobrol", menganggur[i])
    for h in hasil:
        if h["state"] == "santai":
            st, dg = peta[h["nama"]]
            h["state"] = st
            if dg:
                h["dengan"] = tampil[dg]
    return hasil


def rute_otomatis(teks):
    peringkat = skor_rute(teks)
    if not peringkat or peringkat[0][1] < AMBANG_TUNGGAL:
        return None
    return peringkat[0][0]


DAEMON_URL = "http://127.0.0.1:18746"
BROWSER_PY = os.path.realpath(os.path.join(DASAR, "..", "browser", "scripts",
                                           "browser.py"))


def daemon_proxy(path, method="GET", body=None, mentah=False):
    """Teruskan request ke daemon browser Raka; auto-start bila mati.

    Kembalikan (status, content_type, badan_bytes) atau (503, ..., pesan).
    """
    import http.client
    import subprocess
    import time
    import urllib.request

    def coba():
        try:
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(
                DAEMON_URL + path, data=data, method=method,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return (r.status,
                        r.headers.get("Content-Type", "application/json"),
                        r.read())
        except Exception:
            return None

    hasil = coba()
    if hasil is None:
        # auto-start daemon (butuh playwright terinstal + izin Saka tercatat)
        try:
            subprocess.run([sys.executable, BROWSER_PY, "daemon", "start"],
                           capture_output=True, timeout=60)
            for _ in range(20):
                time.sleep(0.5)
                hasil = coba()
                if hasil:
                    break
        except Exception:
            pass
    if hasil is None:
        pesan = ("Daemon browser mati. Pastikan playwright terinstal "
                 "('browser.py install' setelah izin Saka) lalu coba lagi.")
        return (503, "application/json",
                json.dumps({"error": pesan}).encode())
    return hasil


class Handler(BaseHTTPRequestHandler):
    server_version = "KantorHplus/1.0"

    def _auth_ok(self):
        """Wajib lolos bila KANTOR_PASSWORD di-set."""
        if not KANTOR_PASSWORD:
            return True
        import base64
        import hmac
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:].strip()).decode("utf-8", "replace")
                _, _, pw = decoded.partition(":")
                if hmac.compare_digest(pw, KANTOR_PASSWORD):
                    return True
            except Exception:
                pass
        badan = b"butuh password"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Kantor hplus"')
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)
        return False

    def _json(self, obj, kode=200):
        badan = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(kode)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)

    def _baca_body(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except (json.JSONDecodeError, ValueError):
            return {}

    # ---------- GET ----------
    def do_GET(self):
        if not self._auth_ok():
            return
        rute = urllib.parse.urlparse(self.path).path
        if rute in ("/", "/index.html"):
            return self._file("index.html", "text/html")
        if rute == "/api/status":
            return self._json({"agen": state_agen(),
                               "waktu": datetime.now().strftime("%H:%M:%S")})
        if rute == "/api/papan":
            return self._json(tim.baca())
        if rute == "/api/chat":
            log = muat_chat()
            # selipkan permintaan bantuan yg menggantung sebagai prompt
            data = tim.baca()
            butuh = [{"tipe": "butuh", "id": t["id"], "untuk": t["untuk"],
                      "pesan": t["minta_bantuan"]["pesan"],
                      "pada": t["minta_bantuan"]["pada"]}
                     for t in data["tugas"] if t.get("minta_bantuan")
                     and t["minta_bantuan"]["ke"] == "user"]
            return self._json({"chat": log[-50:], "butuh": butuh})
        if rute.startswith("/api/agen/"):
            nama = rute.rsplit("/", 1)[-1]
            if nama not in AGEN_ORDER:
                return self._json({"error": "agen tidak dikenal"}, 404)
            info = muat_agen(nama)
            data = tim.baca()
            tugas = [t for t in data["tugas"] if t["untuk"] == nama]
            reg = os.path.realpath(os.path.join(
                DASAR, "..", "tim", "agen", nama, "keterampilan.json"))
            skill = []
            if os.path.isfile(reg):
                with open(reg, encoding="utf-8") as f:
                    skill = json.load(f).get("keterampilan", [])
            st = next(h for h in state_agen() if h["nama"] == nama)
            return self._json({"info": info, "tugas": tugas,
                               "skill": skill, "state": st["state"]})
        # --- browser Raka: "browser di dalam browser" ---
        if rute == "/api/browser/status":
            kode, ct, badan = daemon_proxy("/status")
            return self._kirim(kode, ct, badan)
        if rute == "/api/browser/layar":
            kode, ct, badan = daemon_proxy("/layar")
            return self._kirim(kode, ct, badan)
        return self._file(rute.lstrip("/"), None)

    def _kirim(self, kode, ct, badan):
        self.send_response(kode)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)

    def _file(self, nama, tipe):
        aman = os.path.realpath(os.path.join(DASAR, nama))
        if not aman.startswith(DASAR) or not os.path.isfile(aman):
            self.send_error(404)
            return
        if not tipe:
            tipe = "text/html" if nama.endswith(".html") else \
                   "application/javascript" if nama.endswith(".js") else \
                   "text/css" if nama.endswith(".css") else \
                   "application/octet-stream"
        with open(aman, "rb") as f:
            badan = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)

    # ---------- POST ----------
    def do_POST(self):
        if not self._auth_ok():
            return
        rute = urllib.parse.urlparse(self.path).path
        body = self._baca_body()
        if rute == "/api/tugas":
            judul = (body.get("judul") or "").strip()
            if not judul:
                return self._json({"error": "judul kosong"}, 400)
            untuk = body.get("untuk") or rute_otomatis(judul) or "nara"
            if untuk not in AGEN_ORDER:
                return self._json({"error": "agen tidak dikenal"}, 400)
            ns = SimpleNamespace(
                judul=judul, untuk=untuk,
                prioritas=body.get("prioritas", "sedang"),
                detail=body.get("detail", ""))
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = tim.cmd_tambah(ns)
            return self._json({"ok": rc == 0, "untuk": untuk,
                               "keluaran": buf.getvalue().strip()})
        if rute == "/api/aksi":
            aksi = body.get("aksi")
            peta = {"ambil": tim.cmd_ambil, "selesai": tim.cmd_selesai,
                    "tunda": tim.cmd_tunda, "beri": tim.cmd_beri,
                    "minta": tim.cmd_minta, "audit": tim.cmd_audit,
                    "ubah-prioritas": tim.cmd_ubah_prioritas}
            if aksi not in peta:
                return self._json({"error": "aksi tidak dikenal"}, 400)
            ns = SimpleNamespace(**{k: v for k, v in body.items()
                                    if k != "aksi"})
            import io, contextlib
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = peta[aksi](ns)
            except TypeError as e:
                return self._json({"error": f"parameter kurang: {e}"}, 400)
            return self._json({"ok": rc == 0,
                               "keluaran": buf.getvalue().strip()})
        if rute == "/api/chat":
            teks = (body.get("teks") or "").strip()
            if not teks:
                return self._json({"error": "pesan kosong"}, 400)
            log = muat_chat()
            log.append({"dari": "user", "teks": teks, "pada": _sekarang()})
            tl = teks.lower()
            data = tim.baca()
            det = balas_deterministik(tl, data)
            agen = None
            if det:
                log.append({"dari": det[0], "teks": det[1], "pada": _sekarang()})
            else:
                agen = rute_otomatis(teks)
                if agen:
                    ns = SimpleNamespace(judul=teks, untuk=agen,
                                         prioritas="sedang",
                                         detail="Dari chat web Kantor hplus.")
                    import io, contextlib
                    with contextlib.redirect_stdout(io.StringIO()):
                        tim.cmd_tambah(ns)
                    # agen menjawab: coba LLM dulu, fallback ke data antrian
                    jwb = tanya_llm(agen, teks)
                    if jwb:
                        log.append({"dari": agen, "teks": jwb,
                                    "pada": _sekarang()})
                    else:
                        d2 = akuisisi_agen(agen, teks)
                        log.append({"dari": d2[0], "teks": d2[1],
                                    "pada": _sekarang()})
                else:
                    log.append({"dari": "komandan",
                                "teks": "Diterima — saya tangani langsung.",
                                "pada": _sekarang()})
            simpan_chat(log)
            return self._json({"ok": True, "rute": agen,
                               "llm": bool(LLM_KEY)})
        if rute == "/api/browser/aksi":
            kode, ct, badan = daemon_proxy("/aksi", "POST", body)
            return self._kirim(kode, ct, badan)
        return self._json({"error": "tidak dikenal"}, 404)

    def log_message(self, fmt, *a):
        sys.stderr.write(f"[{datetime.now():%H:%M:%S}] {fmt % a}\n")


def main():
    ap = argparse.ArgumentParser(description="Kantor hplus — dashboard web tim agen")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"🏢 Kantor hplus live di http://{args.host}:{args.port}")
    print("   Ctrl+C untuk berhenti.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")


if __name__ == "__main__":
    main()
