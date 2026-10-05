# Panduan Instalasi — hplus agent v1

Paket ini berisi kustomisasi *dalam* untuk Hermes agent: skill WiFiLab
buatan sendiri, kepribadian (SOUL.md) Bahasa Indonesia, dan template untuk
skill-skill berikutnya. Semua dipasang di **mesin tempat Hermes berjalan**
(VPS atau perangkatmu) — bukan di chat ini.

## 0. Prasyarat

- Hermes agent sudah terinstall dan `hermes setup` sudah jalan.
  (Panduan resmi: https://github.com/NousResearch/hermes-agent)
- Python 3.8+ tersedia (sudah termasuk di instalasi Hermes/Termux).

## 1. Pasang skill wifilab

```bash
# 1. Masuk ke folder skill Hermes (sesuaikan dengan versimu;
#    umumnya di bawah ~/.hermes)
cd ~/.hermes/skills

# 2. Salin folder wifilab dari paket ini ke sana, sehingga menjadi:
#    ~/.hermes/skills/wifilab/SKILL.md
#    ~/.hermes/skills/wifilab/scripts/wifilab.py

# 3. Pastikan script bisa dijalankan
chmod +x ~/.hermes/skills/wifilab/scripts/wifilab.py

# 4. Tes manual (mesin harus terhubung ke AP WiFiLab saat mengetes)
python3 ~/.hermes/skills/wifilab/scripts/wifilab.py status
```

Kalau IP perangkat bukan 192.168.4.1:

```bash
export WIFILAB_HOST='192.168.4.2'
```

## 2. Pasang kepribadian

```bash
cp SOUL.md ~/.hermes/SOUL.md
```

Lalu restart CLI/gateway Hermes agar dibaca ulang. Kalau di versimu
lokasi/penamaannya berbeda, cek dokumentasi resmi versi tersebut —
konsepnya sama: file persona yang dibaca setiap sesi.

## 3. Aktifkan dan uji dari agen

```bash
hermes tools     # pastikan skill wifilab terdaftar & aktif
hermes           # mulai chat, lalu coba:
```

> cek status wifilab

Agen seharusnya memanggil script skill dan menjawab dengan ringkasan
status — bukan mengarang.

## 4. Sambungkan ke Telegram (opsional, tahap lanjut)

```bash
hermes gateway setup
hermes gateway start
```

Setelah gateway jalan, perintah seperti "pindai wifi sekitar" bisa
diberikan dari Telegram dan agen mengeksekusinya di mesin itu.

## Catatan versi

Hermes berkembang cepat; nama folder dan perintah bisa berubah antar
rilis. Kalau ada yang tidak cocok, jalankan `hermes doctor` dan baca
dokumentasi versi yang terinstall — lalu kabari aku, akan kusesuaikan
paket ini.

## Batas paket ini (jujur)

- Ini adalah lapisan kustom **praktis**: skill + persona + konfigurasi.
- Modifikasi *learning loop* inti (cara agen membuat skill otomatis,
  cara ia mengingat) butuh fork repo dan edit kode sumber Python —
  itu fase 2, setelah instalasi di mesinmu stabil.
