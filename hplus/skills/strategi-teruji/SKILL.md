# Skill: strategi-teruji

Strategi trading hasil **backtest + walk-forward** atas kandidat setup
dari riset intraday 2026-10-03. Dari 10 varian yang diuji (1 tahun, lalu
walk-forward 2–3 tahun), pemenangnya: **XAUUSD H4 SuperTrend(7, 3.0) +
filter ADX(14) > 20** — satu-satunya yang positif bersih setelah biaya
di SEMUA jendela out-of-sample.

## Cara pakai

```bash
python3 scripts/xau_supertrend.py sinyal            # cek sinyal (baca saja)
python3 scripts/xau_supertrend.py sinyal --paper    # + eksekusi paper
python3 scripts/xau_supertrend.py status            # posisi paper saat ini
```

## Aturan strategi (persis seperti yang di-backtest)

- Timeframe H4 (diagregasi dari H1, Yahoo Finance GC=F gratis).
- Selalu pegang arah SuperTrend(7, 3.0): LONG jika up, SHORT jika down.
- **Filter anti-chop**: entry baru hanya jika ADX(14) H4 > 20.
  Jika SuperTrend flip tapi ADX ≤ 20 → FLAT (tunggu).
- Risiko 1% per trade; unit risiko = 3× ATR(10) H4.
- Biaya dimodelkan ECN: 0.10 USD/oz per sisi.

## Hasil walk-forward (jujur, sudah termasuk biaya)

Jendela 12 bulan (9 IS + 3 OOS), geser 3 bulan. Seleksi HANYA dari OOS.

| Setup | Total OOS net R | Trade OOS | Jendela PF>1 |
|---|---|---|---|
| **C5: XAU ST(7,3)+ADX20 ✅** | **+14.8** | 36 | **5/5** |
| C2: XAU ST(10,3)+ADX20 | +13.6 | 36 | 4/5 |
| C4: XAU ST(12,3)+ADX25 | +6.7 | 34 | 4/5 |
| C3: XAU ST(10,2.5)+ADX20 | +3.0 | 51 | 3/5 |
| B3: ETH H1 Donchian | −4.4 | 278 | 4/9 |
| A3: BTC H1 Donchian | −60.3 | 324 | 0/9 |
| A4: BTC M15 Donchian-40 | −224.7 | 713 | 1/9 |
| B2: ETH EMA20-pullback | −421.7 | 1411 | 0/9 |

Catatan: C5 dipilih di antara 4 varian emas yang SEMUANYA positif OOS —
familinya robust, bukan satu parameter kebetulan. Selisih C5 vs C2 kecil.

Temuan terpenting justru yang negatif: strategi breakout/pullback
intraday kripto punya **gross positif tapi net negatif** — biaya
(~0.24% round-trip dengan sizing risiko 1%) memakan ratusan R. Ini cocok
dengan literatur akademik: biaya mendominasi di frekuensi intraday.

## Keterbatasan (WAJIB dibaca)

1. **Sampel tipis**: 36 trade OOS dalam 5 jendela (~7/jendela).
2. **Seleksi parameter dari OOS** (4 varian emas) — bias seleksi ringan;
   mitigasi: semua varian emas positif, bukan cuma pemenangnya.
3. **Periode emas bullish** 2024–2026 menguntungkan trend-following;
   di pasar sideways hasilnya bisa berbeda jauh.
4. **Biaya = ECN** (10¢/oz/sisi). Di akun Standard (spread 20–35¢),
   hasilnya akan lebih buruk — verifikasi di broker masing-masing.
5. **Hanya paper trading.** Skill ini tidak menyentuh uang asli, API
   key, atau order sungguhan. Aturan yang sama dengan skill `sinyal`.
6. Backtest mengasumsikan fill sempurna — slippage saat news spike
   tidak dimodelkan.

Lihat `LAPORAN-BACKTEST.md` untuk detail metodologi dan angka per setup.

## Aturan (WAJIB)

1. **Hanya paper trading.** Tidak ada eksekusi uang asli.
2. Sajikan sebagai **sinyal + alasan + hasil backtest**, bukan perintah
   atau janji profit.
3. Jangan cherry-pick: tunjukkan juga semua setup yang gagal dan
   jendela OOS yang negatif — itu bagian dari kejujuran strategi ini.
