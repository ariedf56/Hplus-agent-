#!/bin/bash
# install-termux.sh — pasang hplus + Kantor GUI auto-start di Termux.
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/install-termux.sh | bash
set -e
echo "[1/5] menyiapkan git..."
pkg install git -y >/dev/null 2>&1 || true
cd ~
if [ -d hplus-agent ]; then
  echo "[2/5] update repo..."
  (cd hplus-agent && git pull -q) || true
else
  echo "[2/5] download hplus..."
  git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
fi
echo "[3/5] pasang skills + SOUL..."
mkdir -p ~/.hermes/skills
cp -r hplus-agent/hplus/skills/* ~/.hermes/skills/
[ -f ~/.hermes/SOUL.md ] && cp ~/.hermes/SOUL.md ~/.hermes/SOUL.md.bak
cp hplus-agent/hplus/SOUL.md ~/.hermes/SOUL.md
echo "[4/5] pasang auto-start Kantor GUI..."
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
fi
echo "[5/5] jalankan + verifikasi..."
if ! curl -sf -m 2 http://127.0.0.1:8080/api/status >/dev/null 2>&1; then
  nohup python3 ~/.hermes/skills/kantor/server.py --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
  sleep 3
fi
hermes --version 2>&1 | head -2
echo "skill: $(ls ~/.hermes/skills | tr '\n' ' ')"
echo ""
echo "SELESAI ✅ — Kantor GUI: http://127.0.0.1:8080"
echo "Mulai sekarang OTOMATIS jalan tiap buka Termux (tanpa ketik apa pun)."
echo "Bookmark URL itu di browser HP biar tinggal tap."
