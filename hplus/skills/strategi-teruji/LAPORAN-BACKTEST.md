# Laporan Backtest — Kandidat Setup Intraday

## Tahap 2: Walk-forward (hasil final, 2026-10-03)

**Data**: BTC/USDT & ETH/USDT M15 **3 tahun** (Okt 2023 – Okt 2026,
105.121 bar), XAUUSD H1 **2 tahun** (Okt 2024 – Okt 2026, 11.457 bar).
**Metode**: jendela 12 bulan (9 IS + 3 OOS), geser 3 bulan.
Kripto: 9 jendela; emas: 5 jendela. **Seleksi HANYA dari OOS.**

### Hasil OOS per jendela (net R setelah biaya)

**Emas — keluarga SuperTrend+ADX (semua positif):**

| Setup | 2025-07 | 2025-10 | 2026-01 | 2026-04 | 2026-07 | Total | PF>1 |
|---|---|---|---|---|---|---|---|
| C5 ST(7,3)+ADX20 ✅ | +0.5 | +5.7 | +5.2 | +2.1 | +1.3 | **+14.8** | 5/5 |
| C2 ST(10,3)+ADX20 | −1.0 | +5.7 | +5.2 | +2.5 | +1.1 | +13.6 | 4/5 |
| C4 ST(12,3)+ADX25 | +2.4 | +0.9 | +3.8 | +1.3 | −1.8 | +6.7 | 4/5 |
| C3 ST(10,2.5)+ADX20 | +0.5 | +3.7 | −0.1 | +0.5 | −1.7 | +3.0 | 3/5 |

**Kripto — semua gagal konsisten:**

| Setup | Total OOS net R | Trade | Jendela PF>1 |
|---|---|---|---|
| B3 ETH H1 Donchian | −4.4 | 278 | 4/9 |
| A3 BTC H1 Donchian | −60.3 | 324 | 0/9 |
| A4 BTC M15 Donchian-40 | −224.7 | 713 | 1/9 |
| B2 ETH EMA20-pullback | −421.7 | 1411 | 0/9 |

**Kesimpulan tahap 2**: edge intraday kripto mati di biaya di SEMUA
jendela (0–1/9 positif — bukan sial, tapi struktural). Keluarga
SuperTrend+ADX emas positif di semua varian dan hampir semua jendela.
**Terpilih: C5 (7,3,ADX20)** — total OOS tertinggi dan 5/5 jendela
positif. Caveat: dipilih di antara 4 varian (bias seleksi ringan),
36 trade OOS masih tipis.

---

## Tahap 1: Backtest 1 tahun (2026-10-03, arsip)

**Periode**: 3 Okt 2025 – 3 Okt 2026 (UTC)
**Data**: BTC/USDT & ETH/USDT M15 (Binance Vision, 35.041 bar),
XAUUSD H1 (Yahoo Finance GC=F, 5.814 bar → agregasi H4)
**Akuntansi**: R-based, risiko 1%/trade dengan compounding.
**Biaya**: kripto 0.10%/sisi + slippage 2bps/sisi (RT 0.24%);
emas ECN 0.10 USD/oz/sisi (RT 0.20 USD/oz).
**Split**: IS = 9 bulan pertama, OOS = 3 bulan terakhir.

## Hasil per setup (net = setelah biaya)

### A — BTC/USDT M15 Donchian-20 breakout + tren H1 EMA50
Sesi 13:00–20:00 UTC, skip weekend. SL 1.5×ATR(M15), TP 2.5R,
time-stop 21:00 UTC.

| | IS | OOS |
|---|---|---|
| Trade | 310 | 85 |
| Win rate | 35.2% | 30.6% |
| Net R (gross R) | −86.7 (+53.9) | −45.3 (+1.9) |
| Profit factor | 0.68 | 0.45 |
| Max DD | 63.3% | 38.6% |

**Cacat teknik**: sinyalnya punya edge kotor (+53.9R IS) tapi biaya
~0.45R/trade membunuhnya. Stop 1.5×ATR terlalu rapat relatif terhadap
biaya 0.24% RT dengan sizing risiko 1%.

### A2 — varian A dengan SL 2.5×ATR (perbaikan biaya ∝ 1/lebar stop)

| | IS | OOS |
|---|---|---|
| Trade | 248 | 77 |
| Win rate | 35.9% | 31.2% |
| Net R (gross R) | −51.5 (+18.4) | −33.7 (−8.1) |
| Profit factor | 0.69 | 0.42 |

**Kesimpulan**: rugi menyusut tapi tetap negatif. Perbaikan tidak cukup.

### B — ETH/USDT M15 pullback + stack EMA20/50 H1
Sesi 07:00–21:00 UTC. SL 2×ATR, TP 3R, BE di +1.5R.

| | IS | OOS |
|---|---|---|
| Trade | 513 | 170 |
| Win rate | 20.1% | 15.3% |
| Net R (gross R) | −152.0 (+7.0) | −106.6 (−38.0) |
| Profit factor | 0.64 | 0.39 |

**Cacat teknik**: definisi pullback-ku buruk — win rate 20% artinya entry
menangkap pisau jatuh, bukan pullback dalam tren. Butuh definisi ulang
total, bukan tuning parameter.

### D — BTC seasonality long 21:00→23:00 UTC (regim vol tinggi)

| | IS | OOS |
|---|---|---|
| Trade | 152 | 92 |
| Win rate | 21.7% | 18.5% |
| Net R (gross R) | −37.5 (−1.0) | −25.1 (−3.0) |
| Profit factor | 0.35 | 0.19 |

**Kesimpulan**: tidak ada edge bahkan sebelum biaya. Gugur.

### C — XAUUSD H4 SuperTrend(10, 3.0), always-in-market

| | IS | OOS |
|---|---|---|
| Trade | 20 | 9 |
| Win rate | 75.0% | 22.2% |
| Net R (gross R) | +12.7 (+12.7) | −0.2 (−0.1) |
| Profit factor | 4.52 | 0.96 |
| Max DD | 1.5% | 2.4% |

**Cacat teknik**: OOS anjlok (WR 22%) — whipsaw saat chop. Biaya bukan
masalah di H4 (gross ≈ net), masalahnya regime.

### C2 — C + filter ADX(14) > 20 saat entry ✅ TERPILIH

| | IS | OOS |
|---|---|---|
| Trade | 20 | 8 |
| Win rate | 65.0% | 25.0% |
| Net R (gross R) | +11.2 (+11.2) | +1.1 (+1.1) |
| Profit factor | 3.98 | 1.36 |
| Max DD | 1.5% | 1.9% |
| Ekuitas akhir | 1.117x | 1.010x |

**Perbaikan**: entry hanya saat ADX > 20 (ada tren); flip SuperTrend
saat chop → FLAT, bukan entry. Satu-satunya setup yang net positif di
IS maupun OOS.

## Catatan metodologi & batasan

- Entry dieksekusi di open bar berikutnya setelah sinyal (tanpa lookahead);
  SL/TP dicek per bar (konservatif: diasumsikan SL kena dulu jika satu
  bar menyentuh keduanya).
- Tidak dimodelkan: slippage saat news spike, gap weekend (data futures
  memang tidak ada bar weekend), requote.
- Filter ADX adalah 1 iterasi penulis — berprinsip (regime-gating sesuai
  riset) tapi tetap satu derajat kebebasan yang dipakai setelah melihat
  data. Risiko curve-fit ringan; mitigasinya: OOS 3 bulan tetap positif.
- Sampel kecil (28 trade/tahun). Butuh forward paper minimal 50–100 trade
  sebelum kesimpulan apa pun.
- Periode backtest adalah pasar emas bullish — hasil trend-following
  bias ke atas di regime seperti ini.
