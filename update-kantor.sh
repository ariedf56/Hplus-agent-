#!/bin/bash
# update-kantor.sh — update GUI Kantor hplus + pastikan auto-start aktif.
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/update-kantor.sh | bash
set -e
cd ~
[ -d hplus-agent ] || git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
(cd hplus-agent && git pull -q)
cp hplus-agent/hplus/skills/kantor/index.html ~/.hermes/skills/kantor/index.html
echo "GUI terbaru terpasang ✅"
if ! grep -q "hplus kantor (auto-start GUI)" ~/.bashrc 2>/dev/null; then
cat >> ~/.bashrc << 'HOOK'
# >>> hplus kantor (auto-start GUI)
if [ -z "$KANTOR_SKIP" ]; then
  if ! curl -sf -m 2 http://127.0.0.1:8080/api/status >/dev/null 2>&1; then
    if [ -f "$HOME/.hermes/skills/kantor/server.py" ]; then
      nohup python3 "$HOME/.hermes/skills/kantor/server.py" --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
      echo "🏢 Kantor hplus live: http://127.0.0.1:8080"
    fi
  fi
fi
# <<< hplus kantor
HOOK
echo "auto-start terpasang ✅"
fi
pkill -f "kantor/server.py" 2>/dev/null || true
sleep 1
nohup python3 ~/.hermes/skills/kantor/server.py --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
sleep 3
python3 - << 'EOF'
import json, urllib.request
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8080/api/status", timeout=10))
    print(f"OK — {len(d['agen'])} agen live ✅")
except Exception:
    print("Server belum merespons, cek /tmp/kantor.log")
EOF
echo "Buka http://127.0.0.1:8080 — mulai sekarang otomatis tiap buka Termux."
