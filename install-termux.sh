#!/bin/bash
# install-termux.sh — pasang hplus ke Hermes yang sudah jalan di Termux.
# Pakai: curl -fsSL .../install-termux.sh | bash
set -e
echo "[1/4] menyiapkan git..."
pkg install git -y >/dev/null 2>&1 || true
cd ~
if [ -d hplus-agent ]; then
  echo "[2/4] update repo..."
  (cd hplus-agent && git pull -q) || true
else
  echo "[2/4] download hplus..."
  git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
fi
echo "[3/4] pasang skills + SOUL..."
mkdir -p ~/.hermes/skills
cp -r hplus-agent/hplus/skills/* ~/.hermes/skills/
[ -f ~/.hermes/SOUL.md ] && cp ~/.hermes/SOUL.md ~/.hermes/SOUL.md.bak
cp hplus-agent/hplus/SOUL.md ~/.hermes/SOUL.md
echo "[4/4] verifikasi..."
hermes --version 2>&1 | head -2
echo "skill: $(ls ~/.hermes/skills | tr '\n' ' ')"
echo ""
echo "SELESAI ✅ — jalankan 'hermes', lalu ketik: status tim"
