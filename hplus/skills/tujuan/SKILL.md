# Skill: tujuan

Pelacak tujuan jangka panjang — padanan tab Goals: mencatat tujuan,
mencatat progres, dan menandai selesai.

## Kapan dipakai

- Pengguna menyampaikan target/aspirasi yang butuh waktu ("aku mau bisa
  ...", "targetku bulan ini ...").
- Pengguna melaporkan kemajuan ("aku sudah berhasil ...").
- Pengguna bertanya "progres tujuanku gimana?".

## Cara pakai

```bash
python3 scripts/tujuan.py tambah "Nama tujuan" --target 2026-12-31
python3 scripts/tujuan.py daftar              # yang aktif saja
python3 scripts/tujuan.py daftar --semua      # termasuk yang selesai
python3 scripts/tujuan.py progres 1 "catatan kemajuan"
python3 tujuan.py selesai 1
```

## Aturan

1. Satu tujuan = satu hasil yang jelas dan terukur. Kalau ucapan pengguna
   masih kabur, tanya dulu sampai konkret sebelum mencatat.
2. Setiap ada kabar kemajuan yang relevan, catat dengan `progres` —
   jangan hanya mengandalkan ingatan percakapan.
3. Rayakan dengan wajar saat tujuan selesai, lalu tawarkan langkah
   berikutnya yang masuk akal.
