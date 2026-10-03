# Skill: kantor 🏢

**Kantor hplus** — Mission Control via browser: dashboard live tempat
setiap agen tampil sebagai karakter animasi. Bisa diakses dari HP/browser.

## Cara pakai

```bash
python3 scripts/server.py --port 8080 --host 0.0.0.0
# Buka: http://<ip-vps>:8080
```

Stdlib saja (tanpa install tambahan).

## Yang bisa dilakukan dari web

1. **Lihat agen live** — tab 🏢 Kantor (agen yang kerja di meja),
   🏠 Rumah (yang tidur 💤), ☕ Kafe (yang makan/ngobrol).
   Animasi gerak terus; status diperbarui tiap 3 detik dari papan tugas.
2. **Klik karakter agen** → modal detail: tugas aktif, riwayat,
   skill, jejak audit + tombol aksi (Selesai, Tunda, Beri bantuan,
   vonis Lulus/Gagal).
3. **Buat tugas** — form "Tugas baru"; agen bisa dipilih manual atau
   **Otomatis** (dirute oleh `rute.py` seperti perintah chat).
4. **Chat tim** — tulis perintah seperti ke Hermes; pesan dirute
   otomatis menjadi tugas agen, Komandan membalas di chat.
5. **Jawab permintaan bantuan** — saat agen `minta --ke user`
   (mis. Raka butuh OTP/CAPTCHA), muncul kartu 🙋 di chat;
   ketik jawabannya → `beri` dijalankan → agen lanjut kerja.

## Arsitektur jujur

- Dashboard membaca/menulis **papan tugas** (`tim.py`) — satu-satunya
  sumber kebenaran. Semua aksi web = perintah `tim.py` yang sama.
- Chat user → dirute → `tambah` tugas. Balasan "Komandan" = status
  routing, bukan LLM sungguhan — LLM-nya tetap Hermes yang terinstal.
- Saat Hermes terinstal di VPS yang sama, Komandan membaca papan/chat
  yang sama → web dan Hermes live terhubung.

## Aturan keselamatan

1. Server hanya dengar di `127.0.0.1` bila belum siap diekspos;
   pakai `--host 0.0.0.0` hanya di jaringan/VPS milik sendiri.
2. Aksi destruktif via web (tunda/audit gagal) mengikuti aturan
   persetujuan yang sama dengan CLI.
3. Jangan letakkan server di internet publik tanpa proteksi
   (password/reverse-proxy) — ini dasbor kendali penuh tim.
