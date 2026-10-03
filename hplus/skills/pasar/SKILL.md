# Skill: pasar

Monitor pasar kripto real-time (harga live dalam Rupiah via API publik
Indodax) + peringatan batas harga otomatis. Ini adalah **asisten
trading**, bukan mesin pencetak uang.

## Kapan dipakai

- "harga btc sekarang berapa?"
- "koin apa yang lagi ramai?"
- "peringatkan aku kalau btc tembus 1,6 miliar"
- Pantauan berkala via cron Hermes.

## Cara pakai

```bash
python3 scripts/pasar.py harga btc
python3 scripts/pasar.py daftar --limit 10
python3 scripts/pasar.py ramai --limit 10
python3 scripts/pasar.py cek btc --atas 1600000000 --bawah 140000000
python3 scripts/pasar.py pantau btc --atas 1600000000 --bawah 140000000 --interval 60
```

`cek` = sekali jalan, cocok dipasang di **cron Hermes** (mis. tiap 15
menit) untuk peringatan otomatis ke Telegram. `pantau` = loop interaktif.

## Aturan (WAJIB)

1. **Ini bukan nasihat keuangan.** Jangan pernah menyajikan data harga
   sebagai rekomendasi beli/jual. Sajikan data, biarkan pengguna yang
   memutuskan.
2. **Risiko nyata.** Ingatkan: kripto sangat fluktuatif, jangan pakai
   uang kebutuhan pokok, dan waspada penipuan berkedok "bot profit
   otomatis".
3. **Tidak ada auto-trading uang asli** lewat skill ini. Kalau pengguna
   meminta bot yang trading sendiri dengan uang sungguhan, tolak dan
   jelaskan risikonya — kecuali ia memahami dan menyetujui eksplisit
   setiap parameternya, dan tetap wajib mengikuti aturan persetujuan
   di SOUL.md.
4. Angka dalam Rupiah; format ribuan Indonesia (titik).
