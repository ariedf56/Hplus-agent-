#!/usr/bin/env bash
# install.sh — memasang hplus agent (Hermes + paket hplus) di VPS Linux.
# Jalankan dari folder hasil extract:  bash install.sh
set -e
HIJAU='\033[0;32m'; KUNING='\033[0;33m'; NC='\033[0m'
say() { echo -e "${HIJAU}[hplus]${NC} $1"; }
warn() { echo -e "${KUNING}[hplus]${NC} $1"; }

say "1/5  Install Hermes resmi (bila belum ada)..."
if command -v hermes >/dev/null 2>&1; then
  say "Hermes sudah terinstall: $(hermes --version 2>/dev/null || echo ok)"
else
  # VERSI DIKUNCI ke commit yang sudah diverifikasi dengan hplus (VERSION.txt).
  # Ini yang menjamin tidak ada bentrok/drift versi: yang terinstall
  # byte-identik dengan yang dites.
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --commit 343500b3
  export PATH="$HOME/.hermes/bin:$PATH"
fi

say "2/5  Memasang skills hplus ke ~/.hermes/skills/..."
mkdir -p ~/.hermes/skills
cp -r hplus/skills/* ~/.hermes/skills/
say "Skills terpasang: $(ls ~/.hermes/skills | tr '\n' ' ')"

say "3/5  Memasang SOUL.md (kepribadian)..."
if [ -f ~/.hermes/SOUL.md ]; then
  cp ~/.hermes/SOUL.md ~/.hermes/SOUL.md.bak
  warn "SOUL.md lama dibackup ke ~/.hermes/SOUL.md.bak"
fi
cp hplus/SOUL.md ~/.hermes/SOUL.md

say "4/5  Browser untuk tim (Playwright + Chromium, opsional tapi disarankan)..."
if python3 -c "import playwright" 2>/dev/null; then
  say "Playwright sudah ada."
else
  warn "Jalankan manual bila butuh skill browser (milik Raka):"
  echo "     pip install playwright && python3 -m playwright install chromium"
fi

say "5/5  Selesai."
echo ""
echo "Langkah berikutnya:"
echo "  1. hermes model            # pilih provider + model LLM"
echo "  2. export LLM_API_KEY=...  # JANGAN tempel key di chat; set di VPS langsung"
echo "  3. hermes                  # ngobrol; coba: 'tampilkan status tim'"
echo "  4. Dashboard Kantor hplus: python3 ~/.hermes/skills/kantor/server.py"
echo "     (ikat ke 127.0.0.1 + beri password bila dibuka ke publik!)"
echo ""
echo "Tim: Nara Koda Vera Raka Tara Saka Ari(🔑). Perintah 'tim ...' / '@agen ...'"
