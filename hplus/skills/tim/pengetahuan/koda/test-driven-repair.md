# Skill: test-driven-repair
Agen: koda | Tier: dewa | Versi: 1
Dari tugas: bawaan-pack | Status: aktif
Diperbarui: 2026-10-04

## Deskripsi
Perbaiki bug dengan TDD terbalik: tulis test yang GAGAL dulu (membuktikan
bug), lalu perbaiki kode sampai test lolos. Menjamin perbaikan benar-benar
menyentuh bug, bukan kebetulan.

## Kapan dipakai
Setiap perbaikan bug oleh Koda — tanpa kecuali untuk bug logika.

## Langkah
1. Tulis/reproduksi: buat test minimal yang mereproduksi bug → jalankan →
   pastikan GAGAL (kalau langsung lolos, test-mu salah).
2. Perbaiki kode (satu perubahan dalam satu waktu).
3. Jalankan test → harus LOLOS. Jalankan juga suite terkait (regresi).
4. Port test ke suite permanen proyek agar bug tak kembali.

## Contoh
Bug: `total_harga(15000, 3)` mengembalikan 15000.
Test dulu: `assertEqual(total_harga(15000, 3), 45000)` → GAGAL.
Perbaiki: `return harga_satuan * jumlah` → LOLOS.

## Batasan
- Untuk bug yang sulit direproduksi otomatis, pakai script reproduksi
  manual + catat langkahnya — prinsipnya sama: bukti gagal dulu.
- Jangan "perbaiki" test agar lolos — itu kecurangan, Saka akan menangkap.
