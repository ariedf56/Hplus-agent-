#!/bin/bash
# kantor-publik.sh — buat Kantor GUI bisa diakses dari internet PUBLIK.
# WAJIB pakai password (dibuat otomatis sekali, disimpan lokal di HP).
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/kantor-publik.sh | bash
# Matikan: Ctrl+C
set -e
cd ~
echo "[1/4] password..."
if [ ! -f ~/.kantor-password ]; then
  head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 16 > ~/.kantor-password
  chmod 600 ~/.kantor-password
  echo "password baru dibuat ✅"
fi
export KANTOR_PASSWORD="$(cat ~/.kantor-password)"
echo "Password Kantor: $KANTOR_PASSWORD"
echo "(catat baik-baik — JANGAN disebar ke siapa pun)"
echo "[2/4] update file terbaru..."
[ -d hplus-agent ] || git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
(cd hplus-agent && git pull -q)
cp -r hplus-agent/hplus/skills/kantor/. ~/.hermes/skills/kantor/
echo "[3/4] restart server (mode terkunci)..."
pkill -f "kantor/server.py" 2>/dev/null || true
sleep 1
nohup env KANTOR_PASSWORD="$KANTOR_PASSWORD" python3 ~/.hermes/skills/kantor/server.py --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
sleep 2
echo "[4/4] buka tunnel publik..."
pkg install cloudflared -y >/dev/null 2>&1 || true
echo ""
echo "=== TUNNEL AKTIF — cari link https://....trycloudflare.com di bawah ==="
echo "=== Buka link itu di browser mana pun + masukkan password di atas ==="
echo "=== Matikan: Ctrl+C ==="
cloudflared tunnel --url http://127.0.0.1:8080
