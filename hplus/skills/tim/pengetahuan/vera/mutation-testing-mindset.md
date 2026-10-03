# Skill: mutation-testing-mindset
Agen: vera | Tier: dewa | Versi: 1
Dari tugas: bawaan-pack | Status: aktif
Diperbarui: 2026-10-04

## Deskripsi
Pastikan test benar-benar menangkap bug, bukan sekadar lolos. Ubah kecil
kode (mutan) — test yang bagus HARUS gagal. Mutan yang lolos = test lemah.

## Kapan dipakai
Saat Vera meragukan kualitas test (terutama test yang ditulis Koda
terburu-buru), atau sebelum memvonis "lulus" untuk kode kritis.

## Langkah
1. Pilih baris logika kunci yang diubah Koda.
2. Buat mutan manual: balik operator (`>` → `>=`), ubah konstanta,
   hapus satu kondisi.
3. Jalankan test → harus GAGAL. Jika LOLOS, test-nya lemah: minta Koda
   memperkuat test, bukan memvonis lulus.
4. Kembalikan mutan, pastikan test lolos kembali.

## Contoh
Kode: `if harga > 0: diskon()`. Mutan: `if harga >= 0:`.
Test `test_tanpa_diskon_saat_nol` harus gagal pada mutan.

## Batasan
- Sampling saja (3–5 mutan per review) — mutasi penuh mahal.
- Untuk proyek Python ada tool `mutmut`/`cosmic-ray`; manual tetap sah.
