# Operasi browser seperti manusia 🌐

Teknik: kendalikan Chromium (Playwright) seolah tangan manusia —
untuk situs berat JavaScript dan alur interaktif (form, login,
pendaftaran) yang tidak bisa dibaca `skills/web` (text-fetch).

## Perintah inti

```bash
B=python3 ~/hermes-custom/skills/browser/scripts/browser.py
$B buka https://situs.com/daftar
$B isi "#email" "nama@email.com"
$B isi "#password" "rahasia"
$B klik "#tombol-daftar"
$B tunggu "#dashboard"        # atau: $B tunggu 3
$B screenshot bukti.png
$B baca                      # teks halaman saat ini
```

Sesi **persisten** (`~/.hermes-browser/`): cookie/login tidak hilang
antar perintah. Browser **headless** (tanpa layar — cocok VPS);
`buka <url> --tampil` untuk mode GUI (butuh X server).

## Pola kerja aman

1. `buka` → `baca`/`screenshot` dulu untuk memahami halaman.
2. Isi form satu per satu (`isi`, `pilih`), verifikasi via screenshot.
3. `klik` tombol aksi → `tunggu` hasil → `baca` konfirmasi.
4. Bila muncul CAPTCHA/OTP/verifikasi HP: **BERHENTI, laporkan ke
   Komandan**. Jangan mengakali — tunggu user menyelesaikan.

## Pola verifikasi manusia (proaktif)

Jangan menunggu mentok baru lapor. Pola yang benar:

1. **Sebelum** klik tombol yang memicu OTP/verifikasi → beri tahu
   Komandan: "langkah berikut mengirim OTP ke HP user, siapkan".
2. Klik → `screenshot` halaman verifikasi → `minta <ID> --ke user
   --pesan "OTP 6 digit dikirim ke +62...; lihat screenshot; balas kodenya"`.
3. BERHENTI (sesi browser tetap hidup/persisten). Tunggu `beri`.
4. Setelah kode diterima: `isi "#otp" "<kode>"` → `klik` verifikasi →
   lanjutkan alur.

CAPTCHA gambar: screenshot + `minta --ke user` ("isi CAPTCHA di
screenshot, atau kerjakan manual lalu bilang 'lanjut'").

## Kendali bersama via daemon (browser di dalam browser)

Untuk alur yang butuh tangan user langsung (OTP/CAPTCHA/login):

1. Pastikan daemon hidup: `browser.py daemon start` (atau biarkan
   dashboard Kantor hplus menyalakannya otomatis).
2. Kerjakan alur seperti biasa — perintah otomatis lewat daemon
   (halaman tidak reload antar perintah).
3. Saat butuh user: `minta <ID> --ke user --pesan "..."` seperti biasa.
4. User membuka **🖥️ Browser Raka** dari dashboard: melihat layar
   live, klik langsung, mengetik OTP, lalu tekan "✅ Selesai,
   lanjutkan" (= `beri`).
5. Lanjutkan alur dari titik berhenti. `daemon stop` bila selesai.

Chromium belum ada? Ikuti protokol: tugas "Izin install" di papan →
Saka audit lulus → `browser.py install` → catat di
`pengetahuan/raka/instalasi.md`.

## Instalasi (butuh izin Saka)

Chromium belum ada? Ikuti protokol: tugas "Izin install" di papan →
Saka audit lulus → `browser.py install` → catat di
`pengetahuan/raka/instalasi.md`.

## Batasan

- Dilarang: spam pendaftaran massal, akun palsu untuk penipuan,
  mengakali verifikasi.
- Kredensial user: dipakai untuk tugas itu saja, tidak dicatat di file.
