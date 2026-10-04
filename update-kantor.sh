#!/bin/bash
# update-kantor.sh — update GUI Kantor hplus ke versi terbaru + jalankan ulang.
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/update-kantor.sh | bash
set -e
cd ~
[ -d hplus-agent ] || git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
cd hplus-agent && git pull -q && cd ~
cp hplus-agent/hplus/skills/kantor/index.html ~/.hermes/skills/kantor/index.html
pkill -f "kantor/server.py" 2>/dev/null || true
sleep 1
nohup python3 ~/.hermes/skills/kantor/server.py --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
sleep 3
python3 - << 'EOF'
import json, urllib.request
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8080/api/status", timeout=10))
    print(f"OK — {len(d['agen'])} agen live ✅")
except Exception as e:
    print("Server belum merespons, cek /tmp/kantor.log")
EOF
echo "Buka di browser HP: http://127.0.0.1:8080"
