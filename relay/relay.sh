#!/bin/bash
# hplus relay — menghubungkan Termux ke Muse via repo GitHub.
# Cara pakai: bash relay.sh   (masukkan token saat diminta)
# Berhenti: Ctrl+C
REPO="ariedf56/Hplus-agent-"
API="https://api.github.com/repos/$REPO/contents"

if [ -z "$GITHUB_TOKEN" ]; then
  echo -n "Token GitHub (hanya dibaca sekali, tidak disimpan permanen): "
  read -s GITHUB_TOKEN; echo
fi
[ -z "$GITHUB_TOKEN" ] && { echo "token kosong, berhenti."; exit 1; }

LAST=""
echo "relay jalan — polling tiap 10 dtk. Ctrl+C untuk berhenti."
while true; do
  MSG=$(curl -fsSL "$API/relay/inbox.json" -H "Authorization: Bearer $GITHUB_TOKEN" 2>/dev/null \
        | python3 -c "import json,sys,base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode())" 2>/dev/null)
  if [ -n "$MSG" ]; then
    ID=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" <<< "$MSG" 2>/dev/null)
    ST=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" <<< "$MSG" 2>/dev/null)
    if [ "$ST" = "pending" ] && [ -n "$ID" ] && [ "$ID" != "$LAST" ]; then
      echo ">> eksekusi $ID"
      CMD=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('cmd',''))" <<< "$MSG" 2>/dev/null)
      OUT=$(timeout 120 bash -c "$CMD" 2>&1 | head -c 40000)
      EC=$?
      PAYLOAD=$(python3 -c "
import json,sys,base64
d={'id':sys.argv[1],'exit':int(sys.argv[2]),'status':'done','output':sys.stdin.read()}
print(base64.b64encode(json.dumps(d).encode()).decode())" "$ID" "$EC" <<< "$OUT")
      curl -fsSL -X PUT -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"relay out $ID\",\"content\":\"$PAYLOAD\"}" \
        "$API/relay/outbox/$ID.json" >/dev/null 2>&1
      LAST="$ID"
      echo "<< selesai $ID (exit $EC)"
    fi
  fi
  sleep 10
done
