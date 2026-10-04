#!/bin/bash
# pasang-llm.sh — sambungkan agen Kantor ke OpenRouter (cukup API key, tanpa pilih model).
# Key diminta langsung di Termux ini saja (tersembunyi) — tidak dikirim ke siapa pun.
# Pakai: curl -fsSL https://raw.githubusercontent.com/ariedf56/Hplus-agent-/main/pasang-llm.sh | bash
set -e
echo "1. Daftar & ambil key di https://openrouter.ai -> Keys (gratis)."
read -s -p "2. Tempel API key (sk-or-v1-...): " KEY < /dev/tty; echo
KEY="$(printf '%s' "$KEY" | tr -d '[:space:]')"
if [ -z "$KEY" ]; then echo "Key kosong — batal."; exit 1; fi
echo "3. Tes key..."
RESP=$(curl -s --max-time 40 https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"openrouter/free","messages":[{"role":"user","content":"jawab dengan satu kata: ok"}],"max_tokens":10}')
if printf '%s' "$RESP" | grep -q '"content"'; then
  JWB=$(printf '%s' "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'].strip())" 2>/dev/null || echo ok)
  echo "   Key VALID ✅ (AI menjawab: $JWB)"
else
  echo "   Key GAGAL ❌ — $(printf '%s' "$RESP" | head -c 200)"
  exit 1
fi
sed -i '/HPLUS_LLM_KEY/d; /HPLUS_LLM_URL/d; /HPLUS_LLM_MODEL/d' ~/.bashrc 2>/dev/null || true
cat >> ~/.bashrc << EOF
export HPLUS_LLM_KEY="$KEY"
export HPLUS_LLM_URL="https://openrouter.ai/api/v1/chat/completions"
export HPLUS_LLM_MODEL="openrouter/free"
EOF
chmod 600 ~/.bashrc 2>/dev/null || true
pkill -f "kantor/server.py" 2>/dev/null || true
echo ""
echo "SELESAI ✅ — buka Termux baru: server Kantor jalan dengan otak AI."
echo "Chat dengan agen mana pun — mereka menjawab sebagai dirinya."
