# Skill: sinyal

Otak trading milik Ari — `local_ai_scanner.py` (Powerful Local AI
Scanner V2) — diintegrasikan ke Hermes dengan pipa data live dari
Binance. Agen bisa memindai setup, mencari entrance, dan mengeksekusi
**paper trading otomatis** setiap saat via cron.

## Kapan dipakai

- "pindai btc" / "ada setup bagus nggak?"
- "cari entrance" — cari peluang entry saat ini
- "cek portofolio paper" — lihat hasil simulasi

## Cara pakai

```bash
python3 scripts/sinyal.py pindai BTC
python3 scripts/sinyal.py pindai XAUUSD        # emas (adaptor khusus, lihat bawah)
python3 scripts/sinyal.py pindai BTC --json     # untuk cron (satu baris JSON)
python3 scripts/sinyal.py pindai BTC --paper    # + eksekusi paper otomatis
python3 scripts/sinyal.py portofolio
python3 scripts/sinyal.py jurnal --limit 10
```

**Berburu entrance tiap saat:** pasang di cron Hermes, mis. tiap
15 menit:

```bash
python3 ~/.hermes/skills/sinyal/scripts/sinyal.py pindai BTC --paper --json
```

Kalau keputusan BUY/SELL dengan confidence ≥ 0.58 muncul, kirim
peringatan ke pengguna (via gateway Telegram). Setiap pindaian tercatat
di `jurnal.json`.

## Cara kerja

1. `data.py` mengambil 200 candle Binance (4h, 1h, 30m, 15m, 5m) +
   spread real dari bookTicker.
2. `indikator.py` menghitung: EMA/SMA, RSI, MACD, ATR, Choppiness,
   Efficiency Ratio, UT Bot, swing S/R, struktur, MSS, FVG.
3. `news.py` + `fundamental.py` + `teknikal.py` menambah tiga lapisan:
   - **News intelligence**: agregat RSS CoinDesk & CoinTelegraph
     (gratis, tanpa API key). Setiap headline 24 jam terakhir dinilai
     sentimennya (bullish/bearish/netral), dampaknya (1–3), dan asetnya.
     Keluaran: `news_bias` global, `news_bias_aset` (bias khusus aset
     yang dipindai), dan `news_shock` (berita dampak-3 berumur <2 jam).
   - **Fundamental**: Fear & Greed Index (api.alternative.me, gratis)
     → bias −1..1.
   - **Teknikal dalam** (opini kedua independen): Bollinger %B,
     Stochastic, ADX + DMI, Pivot Point harian, Fibonacci retracement
     → skor komposit −1..1.
4. `local_ai_scanner.py` (otak milik Ari, **v5: ditambah faktor NEWS
   ke-11** — file asli tersimpan sebagai `local_ai_scanner_original.py`)
   memakan data itu → keputusan BUY/SELL/BUY_LIMIT/SELL_LIMIT/HOLD +
   confidence. Faktor `NEWS` berisi tiga evidence yang dihitung:
   `NEWS_DIRECTION` (bias headline per-aset), `NEWS_SHOCK` (berita
   segar berdampak besar), `MARKET_SENTIMENT` (Fear & Greed).
   Prinsip v5: **berita dihitung, bukan diveto** — berita bullish
   menambah skor beli, berita bearish menambah skor jual, secara
   matematis lewat fusion seperti 10 faktor lainnya.
5. `sinyal.py`: lapisan info (tanpa veto). Saat `NEWS_SHOCK` aktif,
   ukuran posisi paper otomatis **dibagi 2** (logika trading:
   volatilitas tinggi → posisi lebih kecil).
6. Mode `--paper`: kelola portofolio simulasi $1000 — buka posisi saat
   sinyal kuat (risiko 1%, SL 1.5×ATR, TP 3×ATR), tutup saat SL/TP kena.

## Emas (XAUUSD) — v6

`python3 scripts/sinyal.py pindai XAUUSD` memakai jalur khusus berbasis
**riset evidence 2026-10-01** ("cara trading XAUUSD paling terbukti"):

1. **Data** (`data_xauusd.py`): Yahoo Finance v8, gratis tanpa API key —
   `GC=F` (COMEX gold futures, proksi spot) interval 5m/15m/30m/1h
   (H4 diagregasi dari H1) + `DX-Y.NYB` (DXY harian). Struktur data
   yang dimakan otak sama persis dengan kripto.
2. **Faktor DXY ke-12 di otak** (`evaluate_dxy`): DXY uptrend → headwind
   emas (skor −1), DXY downtrend → tailwind (+1), weight 0.8 sebagai
   **konfirmasi, bukan hukum** — riset: korelasi invers ~−0.70..−0.85
   tapi pecah saat risk-off ekstrem. Untuk kripto faktor ini netral.
3. **Sesi UTC**: overlap London–NY 12:00–17:00 (jendela utama), London
   07:00–12:00, NY sore 17:00–21:45 (momentum memudar), **Asia
   00:00–07:00 dead zone** (chop → ukuran posisi paper /2),
   **blackout rollover 21:45–23:15 UTC → TIDAK ADA entry**
   (sesi OFF_PEAK, diblokir otak).
4. **Spread dimodelkan per sesi** (1 pt = $0.01): Asia 20, London 35,
   overlap 45, NY sore 30 pt; scanner emas pakai batas 150 pt
   (spread berita 70–150+ pt itu normal di emas).
5. **Berita emas** (`news.py`): kamus sentimen khusus XAU (dovish/dolar
   melemah/safe-haven = bullish; hawkish/dolar menguat = bearish),
   headline makro (FOMC/CPI/NFP/PCE/PPI/Fed) selalu dampak-3 dan ikut
   dihitung untuk bias emas; sumber makro: MarketWatch + Investing RSS.
   Fear & Greed dinetralkan untuk emas (itu sentimen kripto).
6. **Volume dinetralkan** untuk emas: spot XAUUSD tidak punya tape
   terpusat → sinyal berbasis volume tidak valid; semua indikator
   price-only.

Keterbatasan jujur: `GC=F` adalah futures (ada basis vs spot, kecil
untuk swing H4+); klaim "1.5× ATR optimal" dari riset adalah klaim
praktisi tunggal — anggap parameter awal, validasi dengan backtest
sendiri; belum ada backtest historis XAUUSD di paket ini.

## Kejujuran data (penting)

| Dihitung penuh dari candle | Disederhanakan | Netral (tidak tersedia gratis) |
|---|---|---|
| trend H4/H1/M30, MA/RSI/MACD/ATR, choppiness, KER, UT Bot, struktur M15, MSS M5, S/R H1, zona discount/premium, spread, Bollinger, Stochastic, ADX, Pivot, Fibonacci, news bias per-aset, news shock, Fear & Greed | FVG, deteksi kelelahan, likuiditas sesi, skor sentimen headline (berbasis kata kunci, bukan NLP — agen LLM membaca headline aslinya untuk penilaian akhir) | CVD/order flow, order block detail, mikrostruktur M1, kalender ekonomi (tidak ada feed gratis yang stabil saat diuji — event makro ditangkap via headline) |

Otak aslinya dirancang untuk forex/CFD; di sini diadaptasi ke kripto
spot. Sesi dianggap 24/7, skala spread mengikuti USDT.

## Aturan (WAJIB)

1. **Hanya paper trading.** Skill ini TIDAK punya akses ke exchange,
   TIDAK memegang API key, dan TIDAK mengeksekusi order sungguhan.
   Itu disengaja.
2. **Eksekusi otomatis uang asli DILARANG** — bahkan jika pengguna
   memintanya langsung. Alasannya: (a) header otak sendiri bilang skor
   dan confidence BUKAN jaminan profit; (b) API key exchange di server
   adalah risiko keamanan; (c) pengguna masih pemula — satu bug bisa
   menghabiskan akun saat ia tidur. Tawarkan jalur aman: validasi di
   paper dulu berminggu-minggu; kalau konsisten profit, barulah
   diskusikan integrasi exchange dengan batas risiko ketat DAN
   persetujuan per-trade sesuai SOUL.md.
3. Sajikan keputusan sebagai **sinyal + alasan**, bukan perintah.
   Keputusan uang tetap milik pengguna.
4. Jangan cherry-pick: tampilkan juga HOLD dan confidence rendah —
   itu informasi, bukan kegagalan.
