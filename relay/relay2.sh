#!/bin/bash
# hplus relay v2 — Termux terhubung ke Muse via ntfy.sh
# TANPA token, TANPA login. Pakai: bash relay2.sh   Berhenti: Ctrl+C
TOPIC="hplus-ar-Nbjt8qQjYtb9"
LAST="$HOME/.hplus-relay2-last"
touch "$LAST" 2>/dev/null
lastid=$(cat "$LAST" 2>/dev/null)

command -v python3 >/dev/null || { echo "butuh python3: pkg install python -y"; exit 1; }
command -v curl >/dev/null || { echo "butuh curl: pkg install curl -y"; exit 1; }

echo "======================================"
echo " hplus relay v2 JALAN"
echo " Menunggu perintah dari Muse."
echo " Semua perintah tampil di sini — awasi langsung."
echo " Berhenti kapan saja: Ctrl+C"
echo "======================================"

poll_cmd() {
  local since="all"; [ -n "$lastid" ] && since="$lastid"
  curl -fsSL --max-time 25 "https://ntfy.sh/${TOPIC}-cmd/json?since=${since}" 2>/dev/null \
    | python3 -c "
import json,sys
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    try: d=json.loads(line)
    except: continue
    if d.get('event')=='message':
        print(d['id']+' '+d.get('message',''))
" 2>/dev/null
}

while true; do
  while read -r mid rest; do
    [ -z "$mid" ] && continue
    [ "$mid" = "$lastid" ] && continue
    id="${rest%% *}"; b64="${rest#* }"
    echo ">> perintah $id"
    cmd=$(echo "$b64" | base64 -d 2>/dev/null)
    echo "   $cmd" | head -c 300; echo
    out=$(timeout 120 bash -c "$cmd" 2>&1 | head -c 2500)
    ec=$?
    bout=$(printf '%s' "$out" | base64 -w0)
    curl -fsSL --max-time 20 -d "$id $ec $bout" "https://ntfy.sh/${TOPIC}-out" >/dev/null 2>&1
    echo "$mid" > "$LAST"
    lastid="$mid"
    echo "<< terkirim ($id, exit $ec)"
  done < <(poll_cmd)
  sleep 5
done
