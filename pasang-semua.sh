#!/bin/bash
# pasang-semua.sh — SATU perintah untuk semuanya: Hermes resmi + hplus + Kantor GUI.
# Dipakai di Termux HP. Kalau Hermes belum ada, dipasang otomatis dari installer
# resmi (https://hermes-agent.nousresearch.com/install.sh). Tidak ada download
# manual terpisah — semua otomatis.
#
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/pasang-semua.sh | bash
set -e

echo "=== [1/6] Hermes ==="
if command -v hermes >/dev/null 2>&1; then
  echo "Hermes sudah ada: $(hermes --version 2>&1 | head -1)"
else
  echo "Hermes belum ada — pasang dari installer resmi (bisa beberapa menit)..."
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  echo "Hermes terpasang: $(hermes --version 2>&1 | head -1)"
fi

echo "=== [2/6] ambil hplus ==="
pkg install git -y >/dev/null 2>&1 || true
cd ~
if [ -d hplus-agent ]; then
  echo "update repo hplus..."
  (cd hplus-agent && git pull -q) || true
else
  echo "download hplus..."
  git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
fi

echo "=== [3/6] pasang skills hplus ==="
mkdir -p ~/.hermes/skills
cp -r hplus-agent/hplus/skills/* ~/.hermes/skills/
echo "skills: $(ls ~/.hermes/skills | tr '\n' ' ')"

echo "=== [4/6] SOUL hplus (aman: yang lama di-backup) ==="
if [ -f ~/.hermes/SOUL.md ]; then
  BAK=~/.hermes/SOUL.md.bak.$(date +%Y%m%d-%H%M%S)
  cp ~/.hermes/SOUL.md "$BAK"
  echo "SOUL lama dibackup ke: $BAK"
fi
cp hplus-agent/hplus/SOUL.md ~/.hermes/SOUL.md
echo "SOUL hplus terpasang."

echo "=== [5/6] auto-start Kantor GUI ==="
sed -i '/# >>> hplus kantor/,/# <<< hplus kantor/d' ~/.bashrc 2>/dev/null || true
{ cat >> ~/.bashrc << 'HOOK_EOF'
# >>> hplus kantor (auto-start GUI)
if [ -z "$KANTOR_SKIP" ]; then
  [ -f "$HOME/.kantor-password" ] && export KANTOR_PASSWORD="$(cat $HOME/.kantor-password)"
  KODE=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
  if [ "$KODE" != "200" ] && [ "$KODE" != "401" ]; then
    if [ -f "$HOME/.hermes/skills/kantor/server.py" ]; then
      nohup env KANTOR_PASSWORD="$KANTOR_PASSWORD" python3 "$HOME/.hermes/skills/kantor/server.py" >/dev/null 2>&1 &
      echo "🏢 Kantor hplus live: http://127.0.0.1:8080"
    fi
  fi
fi
# <<< hplus kantor
HOOK_EOF
}

echo "=== [6/6] jalankan + verifikasi ==="
[ -f ~/.kantor-password ] && export KANTOR_PASSWORD="$(cat ~/.kantor-password)"
KODE=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
if [ "$KODE" != "200" ] && [ "$KODE" != "401" ]; then
  nohup env KANTOR_PASSWORD="$KANTOR_PASSWORD" python3 ~/.hermes/skills/kantor/server.py >/dev/null 2>&1 &
  sleep 3
fi
echo ""
echo "hermes: $(hermes --version 2>&1 | head -1)"
echo "kantor: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/status)"
echo ""
echo "SELESAI ✅ — satu perintah, semuanya terpasang."
echo "Kantor GUI: http://127.0.0.1:8080  (bookmark di browser HP)"
echo "Coba perintahkan Hermes: 'cek papan tim pakai tim.py daftar'"
