# Skill: wifilab

Kendali perangkat lab WiFi milik pengguna (firmware WiFiLab v1.0 di ESP8266)
langsung dari percakapan. Skill ini adalah jembatan HTTP antara agen dan
perangkat — kemampuan yang tidak dimiliki instalasi Hermes standar mana pun.

## Kapan dipakai

Pakai skill ini ketika pengguna meminta hal yang berkaitan dengan perangkat
WiFiLab-nya, misalnya:

- "cek status wifilab" / "alat lab masih jalan?"
- "pindai wifi sekitar" / "lihat jaringan di sekitar lab"
- "pantau lab" / "ada klien nyangkut berapa?"
- "hentikan serangan"
- "lihat kredensial tertangkap"

## Cara pakai

Semua aksi lewat script `scripts/wifilab.py`. Jalankan dari folder skill ini.
Perangkat harus terjangkau via HTTP (default `http://192.168.4.1` — yaitu
ketika mesin agen terhubung ke AP `WiFiLab`). Kalau IP-nya berbeda, set
environment variable `WIFILAB_HOST` sebelum menjalankan script.

```bash
python3 scripts/wifilab.py status        # ringkasan status alat
python3 scripts/wifilab.py pindai        # pindai jaringan, tampilkan tabel
python3 scripts/wifilab.py pantau        # snapshot: mode, klien, deauth
python3 scripts/wifilab.py berhenti      # hentikan serangan yang berjalan
python3 scripts/wifilab.py kredensial    # jumlah + samaran kredensial
python3 scripts/wifilab.py serang --jenis beacon --jumlah 10
```

Pemetaan bahasa natural → perintah:

| Pengguna bilang | Jalankan |
|---|---|
| status / masih jalan? | `status` |
| pindai / scan sekitar | `pindai` |
| pantau / awasi | `pantau` |
| berhenti / stop | `berhenti` |
| kredensial tertangkap | `kredensial` |

## Aturan keselamatan (WAJIB)

1. **Hanya untuk lab milik pengguna.** Perintah `serang` (deauth, beacon
   spam, evil twin, rogue AP) hanya boleh dijalankan di jaringan milik
   pengguna atau yang ia punya izin tertulis untuk diuji.
2. **Minta konfirmasi dulu** sebelum menjalankan `serang` jenis apa pun.
   Jelaskan apa yang akan terjadi, tunggu jawaban "ya".
3. Perintah baca (`status`, `pindai`, `pantau`, `kredensial`) aman dan boleh
   langsung dijalankan.
4. Jangan pernah menampilkan password kredensial apa adanya kecuali pengguna
   memintanya eksplisit — default-nya tersamar.

## Format jawaban

- Sajikan hasil pindai sebagai daftar ringkas: SSID, sinyal (dBm), kanal,
  enkripsi. Jangan menumpahkan JSON mentah ke pengguna.
- Untuk `pantau`, beri satu baris ringkasan + sorotan jika ada yang aneh
  (mis. deauth terdeteksi naik tiba-tiba).
