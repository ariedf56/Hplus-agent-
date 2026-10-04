#!/bin/bash
# update-kantor.sh — update GUI Kantor hplus + pastikan auto-start aktif.
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/update-kantor.sh | bash
set -e
cd ~
[ -d hplus-agent ] || git clone -q https://github.com/ariedf56/Hplus-agent- hplus-agent
(cd hplus-agent && git pull -q)
cp -r hplus-agent/hplus/skills/kantor/. ~/.hermes/skills/kantor/
echo "GUI + server terbaru terpasang ✅"
sed -i '/# >>> hplus kantor/,/# <<< hplus kantor/d' ~/.bashrc 2>/dev/null || true
{ cat >> ~/.bashrc << 'HOOK_EOF'
# >>> hplus kantor (auto-start GUI)
if [ -z "$KANTOR_SKIP" ]; then
  [ -f "$HOME/.kantor-password" ] && export KANTOR_PASSWORD="$(cat "$HOME/.kantor-password")"
  KODE=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
  if [ "$KODE" != "200" ] && [ "$KODE" != "401" ]; then
    if [ -f "$HOME/.hermes/skills/kantor/server.py" ]; then
      nohup env KANTOR_PASSWORD="$KANTOR_PASSWORD" python3 "$HOME/.hermes/skills/kantor/server.py" --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
      echo "🏢 Kantor hplus live: http://127.0.0.1:8080"
    fi
  fi
fi
# <<< hplus kantor
HOOK_EOF
}
echo "auto-start terpasang ✅"
[ -f ~/.kantor-password ] && export KANTOR_PASSWORD="$(cat ~/.kantor-password)"
pkill -f "kantor/server.py" 2>/dev/null || true
sleep 1
nohup env KANTOR_PASSWORD="$KANTOR_PASSWORD" python3 ~/.hermes/skills/kantor/server.py --host 127.0.0.1 --port 8080 >/tmp/kantor.log 2>&1 &
sleep 3
KODE=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
if [ "$KODE" = "200" ] || [ "$KODE" = "401" ]; then echo "Server live ✅ (kode $KODE)"; else echo "Cek /tmp/kantor.log"; fi
echo "Buka http://127.0.0.1:8080 — otomatis tiap buka Termux."
