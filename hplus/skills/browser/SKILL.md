# Skill: browser 🌐

Operasi browser **seperti manusia** untuk Raka 🔍: buka halaman,
klik, isi form, baca isi, screenshot, daftar akun, dan alur web
lain yang butuh JavaScript / interaksi (yang tidak bisa dilakukan
`skills/web` yang text-based).

## Cara pakai

```bash
python3 scripts/browser.py periksa            # cek playwright+chromium terinstal?
python3 scripts/browser.py install            # install playwright+chromium (butuh izin Saka!)
python3 scripts/browser.py buka https://example.com
python3 scripts/browser.py baca               # teks halaman saat ini
python3 scripts/browser.py judul
python3 scripts/browser.py klik "#tombol-daftar"
python3 scripts/browser.py isi "#email" "nama@email.com"
python3 scripts/browser.py pilih "#negara" "Indonesia"
python3 scripts/browser.py tunggu 3
python3 scripts/browser.py screenshot bukti.png
python3 scripts/browser.py url
python3 scripts/browser.py tutup
```

Semua perintah memakai **sesi persisten** (`~/.hermes-browser/`):
cookie & login tetap tersimpan antar perintah, jadi alur multi-langkah
(buka → isi form → klik daftar → verifikasi) bisa dijalankan bertahap.

## Daemon: sesi browser hidup 🖥️ (milik TIM)

Untuk **kendali bersama agen + user** ("browser di dalam browser"
di dashboard Kantor hplus). Walau skill ini milik Raka, sesi browser
bisa dipakai **agen mana pun** yang meminta bantuan user
(`minta --ke user --pesan "tolong isi ... di browser"`):

```bash
python3 scripts/browser.py daemon start   # hidupkan sesi (latar)
python3 scripts/browser.py daemon status
python3 scripts/browser.py daemon stop
```

Saat daemon hidup, semua perintah (`buka/klik/isi/ketik/...`)
dieksekusi pada **halaman yang sama tanpa reload** — Raka dan user
bisa bergantian mengendalikan. Perintah khusus kendali user:

```bash
python3 scripts/browser.py klik-xy 0.5 0.3  # klik koordinat fraksi layar
python3 scripts/browser.py ketik "483920"   # ketik pada fokus
python3 scripts/browser.py tombol Enter     # Enter/Tab/Escape
```

Dashboard (`skills/kantor`) men-streaming layar daemon ke browser user
dan meneruskan klik/ketikan balik — user bisa isi OTP/CAPTCHA langsung
di sesi Raka, lalu tekan "✅ Selesai, lanjutkan" (= `beri` di papan).
Daemon berhenti otomatis bila menganggur 30 menit.

Browser berjalan **headless** (tanpa layar, cocok untuk VPS).
Tambahkan `--tampil` pada `buka` untuk mode GUI (butuh X server/Xvfb).

## Instalasi mandiri (protokol wajib)

Raka **dilarang** menjalankan `install` sebelum ada **izin Saka**:

1. Raka buat tugas di papan: `tambah "Izin install: playwright+chromium
   (skill browser)" --untuk saka --prioritas tinggi`
2. Saka audit (`tugas selesai` → `audit --vonis lulus --catatan
   "disetujui: <alasan>"`). Vonis `lulus` = izin resmi, tercatat permanen.
3. Raka jalankan `browser.py install`, lalu catat di
   `pengetahuan/raka/instalasi.md` (apa, kenapa, kapan, siapa menyetujui).

Saka menilai: kebutuhan nyata untuk skill? sumber resmi
(PyPI + `playwright install` resmi)? cakupan wajar (tanpa sudo)?

## Aturan keselamatan (WAJIB)

1. **Izin Saka dulu** untuk setiap instalasi (lihat protokol di atas).
   Tanpa jejak audit `lulus`, instalasi = pelanggaran komando.
2. **Sumber resmi saja**: `pip install <paket>` (PyPI) dan
   `playwright install` resmi. Dilarang `curl ... | bash`,
   script installer acak, atau PPA tak dikenal.
3. **Tanpa sudo** kecuali Saka menyetujui eksplisit + ada alasan teknis.
   Utamakan `--user` / ruang pengguna.
4. **Form & akun**: boleh isi form dan mendaftar akun **atas perintah
   user/Komandan**. Dilarang keras: spam pendaftaran massal, akun palsu
   untuk penipuan, atau mengakali verifikasi (CAPTCHA farm, nomor
   sekali-pakai untuk abuse).
5. **Verifikasi manusia (OTP/CAPTCHA)**: akan mentok — JANGAN mengakali.
   Prosedur proaktif: SEBELUM menekan tombol yang memicu OTP, beri tahu
   Komandan ("langkah berikut mengirim OTP ke HP user"). Saat mentok:
   amankan sesi (persisten otomatis), ambil `screenshot`, lalu
   `minta <ID> --ke user --pesan "OTP 6 digit dikirim ke +62...;
   lihat screenshot bukti.png; balas kodenya"`. BERHENTI, tunggu `beri`
   → `isi` kode ke field → lanjutkan alur.
6. **Data login milik user**: kredensial yang dimasukkan user hanya
   dipakai untuk tugas itu, tidak dicatat di file/log (sesi browser
   menyimpan cookie, bukan password mentah).
7. Setiap instalasi **dicatat** di `pengetahuan/<agen>/instalasi.md`.
