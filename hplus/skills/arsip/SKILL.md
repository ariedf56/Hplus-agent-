# Skill: arsip

Gudang file pribadi — padanan tab Library: menyimpan file penting ke
arsip terkategorikan yang mudah dicari kembali.

## Kapan dipakai

- Pengguna memintamu menyimpan file ("simpan ini", "arsipkan laporan").
- Pengguna mencari file yang pernah disimpan ("cari file tentang ...").

## Cara pakai

```bash
python3 scripts/arsip.py simpan /path/ke/file --kategori laporan --ket "Laporan mingguan lab"
python3 scripts/arsip.py daftar
python3 scripts/arsip.py daftar --kategori laporan
python3 scripts/arsip.py daftar --cari wifilab
```

Kategori bebas: laporan, firmware, catatan, dll. Buat kategori baru
sesuai kebutuhan pengguna.

## Aturan

1. Jangan mengarsip file kredensial (berisi password, API key, token).
   Tolak dengan sopan dan jelaskan kenapa.
2. Selalu beri keterangan singkat saat menyimpan agar mudah dicari.
3. Saat pengguna meminta file, sebutkan id arsipnya.
