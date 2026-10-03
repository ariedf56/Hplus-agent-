#!/usr/bin/env python3
"""
web.py — pencarian web dan pembaca halaman untuk Hermes.
Tanpa pip install. Hanya pustaka bawaan Python.

Strategi pencarian berlapis (otomatis, dari yang terbaik ke cadangan):
  1. Brave Search API  — kalau env BRAVE_API_KEY diisi (gratis di
     https://brave.com/search/api). Hasil web penuh kualitas terbaik.
  2. DuckDuckGo HTML   — tanpa key; di sebagian IP datacenter DDG
     menampilkan halaman "anomaly" dan backend ini dilewati otomatis.
  3. DuckDuckGo Instant Answer API — ringkasan + topik terkait.
  4. Wikipedia API     — selalu bisa, cakupannya ensiklopedia saja.

Pemakaian:
    python3 web.py cari "cara install docker ubuntu"
    python3 web.py cari "esp8266 pinout" --jumlah 3
    python3 web.py baca https://example.com/artikel
"""
import html as htmlmod
import json
import os
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def ambil(url, timeout=15, header_tambahan=None):
    hdr = dict(UA)
    if header_tambahan:
        hdr.update(header_tambahan)
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


# ---------- backend 1: Brave (butuh API key gratis) ----------
def _cari_brave(query, jumlah):
    key = os.environ.get("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    try:
        url = ("https://api.search.brave.com/res/v1/web/search?q="
               + urllib.parse.quote(query) + f"&count={jumlah}")
        d = json.loads(ambil(url, header_tambahan={"X-Subscription-Token": key}))
        out = []
        for r in d.get("web", {}).get("results", [])[:jumlah]:
            out.append({"judul": r.get("title", ""),
                        "url": r.get("url", ""),
                        "cuplikan": r.get("description", "")})
        return out
    except Exception:
        return []


# ---------- backend 2: DuckDuckGo HTML (tanpa key) ----------
def _cari_ddg_html(query, jumlah):
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        halaman = ambil(url)
        if "anomaly" in halaman.lower():
            return []  # IP dibatasi DDG -> lanjut ke backend berikut
        hasil = []
        for m in re.finditer(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                halaman, re.S):
            link, judul = m.group(1), m.group(2)
            judul = htmlmod.unescape(re.sub(r"<[^>]+>", "", judul)).strip()
            if link.startswith("//duckduckgo.com/l/"):
                q = urllib.parse.urlparse("https:" + link).query
                link = urllib.parse.parse_qs(q).get("uddg", [""])[0] or link
            if not link.startswith("http"):
                continue
            hasil.append({"judul": judul, "url": link, "cuplikan": ""})
            if len(hasil) >= jumlah:
                break
        return hasil
    except Exception:
        return []


# ---------- backend 3: DuckDuckGo Instant Answer ----------
def _cari_ddg_instant(query, jumlah):
    try:
        url = ("https://api.duckduckgo.com/?q=" + urllib.parse.quote(query)
               + "&format=json&no_html=1&skip_disambig=1")
        d = json.loads(ambil(url))
        hasil = []
        if d.get("Abstract"):
            hasil.append({"judul": d.get("Heading") or query,
                          "url": d.get("AbstractURL", ""),
                          "cuplikan": d.get("Abstract", "")})
        for t in d.get("RelatedTopics", []):
            if isinstance(t, dict) and t.get("FirstURL"):
                hasil.append({"judul": t.get("Text", "")[:80],
                              "url": t["FirstURL"],
                              "cuplikan": t.get("Text", "")})
            if len(hasil) >= jumlah:
                break
        return hasil[:jumlah]
    except Exception:
        return []


# ---------- backend 4: Wikipedia ----------
def _cari_wikipedia(query, jumlah):
    hasil = []
    for wiki in ("id", "en"):  # coba Indonesia dulu, lalu Inggris
        try:
            url = (f"https://{wiki}.wikipedia.org/w/api.php?action=query"
                   "&list=search&srsearch=" + urllib.parse.quote(query)
                   + f"&format=json&srlimit={jumlah}")
            d = json.loads(ambil(url))
            for r in d.get("query", {}).get("search", [])[:jumlah]:
                cuplikan = htmlmod.unescape(re.sub(r"<[^>]+>", "",
                                                   r.get("snippet", "")))
                hasil.append({
                    "judul": r.get("title", ""),
                    "url": f"https://{wiki}.wikipedia.org/wiki/"
                           + urllib.parse.quote(
                               r.get("title", "").replace(" ", "_")),
                    "cuplikan": cuplikan})
            if hasil:
                break
        except Exception:
            continue
    return hasil


def cari(query, jumlah=5):
    for backend in (_cari_brave, _cari_ddg_html, _cari_ddg_instant,
                    _cari_wikipedia):
        hasil = backend(query, jumlah)
        if hasil:
            return hasil
    return []


# ---------- pembaca halaman ----------
def baca(url, batas=6000):
    halaman = ambil(url)
    halaman = re.sub(
        r"(?is)<(script|style|noscript|header|footer|nav)[^>]*>.*?</\1>",
        " ", halaman)
    teks = re.sub(r"(?s)<[^>]+>", " ", halaman)
    teks = htmlmod.unescape(teks)
    teks = re.sub(r"[ \t]+", " ", teks)
    teks = re.sub(r"\n\s*\n+", "\n\n", teks).strip()
    if len(teks) > batas:
        teks = teks[:batas] + "\n\n... (dipotong)"
    return teks


def main(argv):
    if len(argv) < 3 or argv[1] not in ("cari", "baca"):
        print(__doc__)
        sys.exit(1)
    try:
        if argv[1] == "cari":
            jumlah = 5
            if "--jumlah" in argv:
                jumlah = int(argv[argv.index("--jumlah") + 1])
            hasil = cari(argv[2], jumlah)
            if not hasil:
                print("Tidak ada hasil dari semua sumber pencarian.")
                return
            for i, h in enumerate(hasil, 1):
                print(f"{i}. {h['judul']}\n   {h['url']}")
                if h.get("cuplikan"):
                    print(f"   {h['cuplikan'][:200]}")
                print()
        else:
            print(baca(argv[2]))
    except Exception as e:  # noqa: BLE001
        print(f"Gagal: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
