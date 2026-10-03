# Skill: web

Pencarian web dan pembaca halaman — padanan kemampuanku menjelajah
internet — tanpa layanan berbayar.

## Kapan dipakai

- Pengguna minta informasi terkini dari internet ("cari ...", "berita
  terbaru tentang ...", "harga ...")
- Perlu membaca isi sebuah URL yang diberikan pengguna atau ditemukan
  dari pencarian.

## Cara pakai

```bash
python3 scripts/web.py cari "kata kunci"              # 5 hasil teratas
python3 scripts/web.py cari "kata kunci" --jumlah 3   # batasi hasil
python3 scripts/web.py baca https://contoh.com/artikel
```

## Cara kerja pencarian (otomatis, berlapis)

1. **Brave Search API** — kalau `BRAVE_API_KEY` diisi (daftar gratis di
   https://brave.com/search/api). Hasil web penuh, kualitas terbaik.
2. **DuckDuckGo HTML** — tanpa key; di sebagian IP server DDG menolak
   dan backend ini dilewati sendiri.
3. **DuckDuckGo Instant Answer** — ringkasan + topik terkait.
4. **Wikipedia (id, lalu en)** — selalu bisa, cakupan ensiklopedia.

Tanpa API key pun skill tetap berguna via lapisan 2–4. Untuk kualitas
setara mesin pencari penuh, minta pengguna mendaftarkan Brave API key
gratis dan menyimpannya sebagai environment variable `BRAVE_API_KEY`
— jangan pernah ditempel di chat.

## Aturan

1. Hasil pencarian bisa basi — untuk harga/ketersediaan/jadwal, verifikasi
   dengan `baca` ke sumber aslinya sebelum menjawab.
2. Selalu sebutkan sumber (judul + URL) saat menyampaikan fakta dari web.
3. Jangan membuka URL yang terlihat mencurigakan (phishing/typosquatting).
4. Keluaran `baca` dipotong otomatis; kalau informasi yang dicari belum
   ketemu di potongan itu, katakan terus terang.
