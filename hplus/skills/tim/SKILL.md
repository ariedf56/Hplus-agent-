# Skill: tim

Sistem multi-agent Hermes: Komandan (Hermes sendiri) mendelegasikan
pekerjaan ke 6 agen spesialis, masing-masing dengan peran, avatar, dan
warna khas — dan masing-masing dibekali 4 tier skill (🌱 dasar,
🎯 khusus, ⚡ dewa, ➕ tambahan). Roster lengkap + aturan main ada di
`AGEN.md`; definisi tiap peran + tier skill-nya ada di `peran/<nama>.md`.

## Kapan dipakai

Pakai skill ini ketika pengguna memberi tugas yang:

- terdiri dari 3+ langkah → pecah via Nara, kerjakan paralel/berurutan;
- butuh keahlian campur (riset + kode + verifikasi, atau analisis pasar);
- eksplisit menyebut agen ("suruh Koda buatkan...", "minta Raka riset...").

Tugas sepele satu langkah → kerjakan langsung, jangan libatkan tim.

## Cara pakai

Papan tugas: `python3 scripts/tim.py` dari folder skill ini.

```bash
python3 scripts/tim.py tambah "Riset API Telegram Bot" --untuk raka --prioritas tinggi --detail "cari cara kirim pesan via HTTP"
python3 scripts/tim.py daftar                    # semua tugas
python3 scripts/tim.py daftar --status antri     # filter status
python3 scripts/tim.py daftar --untuk koda       # filter agen
python3 scripts/tim.py ambil T-001 --oleh raka   # antri -> jalan
python3 scripts/tim.py selesai T-001 --hasil "pakai POST ke api.telegram.org/bot<token>/sendMessage"
python3 scripts/tim.py audit T-001 --vonis lulus --catatan "sumber lengkap"
python3 scripts/tim.py audit T-002 --vonis gagal --catatan "tanpa bukti uji, perbaiki dulu"
python3 scripts/tim.py tunda T-003 --alasan "ada perintah mendesak"   # interupsi: jalan -> antri
python3 scripts/tim.py ubah-prioritas T-004 --prioritas mendesak
python3 scripts/tim.py laporan-kinerja                 # rapor kinerja tiap agen
python3 scripts/tim.py minta T-001 --ke user --pesan "OTP 6 digit dikirim ke HP"  # jeda, minta bantuan
python3 scripts/tim.py beri T-001 --isi "OTP: 483920" # bantuan diterima, tugas lanjut
python3 scripts/tim.py butuh --batas-jam 2  # permintaan bantuan yang menggantung; tandai TERLAMBAT
python3 scripts/tim.py status                    # kesibukan tiap agen
```

**Aman untuk paralel:** papan memakai file lock + tulis atomik —
banyak agen boleh baca/tulis bersamaan tanpa data hilang.
**Jangan lupa `butuh`:** jalankan berkala (mis. cron tiap 2 jam);
yang ⚠️ TERLAMBAT → ingatkan user/agen sekali lagi atau ambil alih.

## Memori & konteks (`ingat.py`)

```bash
python3 scripts/ingat.py catat --agen bersama --jenis preferensi \
  --topik "Gaya user" --isi "Ari ingin jawaban langsung, bahasa Indonesia"
python3 scripts/ingat.py cari "trading"          # cari memori relevan
python3 scripts/ingat.py pelajaran               # pelajaran dari audit gagal
python3 scripts/ingat.py konteks                 # konteks tim saat ini
python3 scripts/ingat.py konteks-tambah --bagian keputusan --isi "..."
```

Aturan: catat preferensi/fakta/pelajaran penting; JANGAN catat rahasia
(password/key — itu ranah `kredensial.py`). Memori relevan + konteks
disuntik otomatis ke setiap delegasi agen.

Vonis `gagal` otomatis membuka lagi tugasnya (status → `jalan`) dan
menempel catatan perbaikan wajib. Jejak audit tersimpan permanen dan
terlihat di `daftar --detail`.

**Router perintah user** — `python3 scripts/rute.py "<perintah>"`:

```bash
python3 scripts/rute.py "koda, buatkan bot telegram"  # vokatif → Koda pasti
python3 scripts/rute.py "gimana sinyal btc hari ini"  # kata kunci → Tara
python3 scripts/rute.py "tulis bot dan riset API-nya"  # multi-agen → batch
```

Output: baris `# RUTE: <agen>` + kode `delegate_task(...)` siap
dieksekusi via `execute_code`. Perintah mentah user diteruskan ke agen —
agen menerjemahkannya mandiri (lihat "Menerjemahkan perintah user" di
tiap `peran/*.md`).

## Sistem belajar (skill baru & upgrade)

Setiap agen wajib belajar skill baru dan menyimpannya — protokol lengkap
di `BELAJAR.md`. Registry per agen: `agen/<nama>/keterampilan.json`;
file skill: `pengetahuan/<agen>/<nama>.md`.

```bash
python3 scripts/belajar.py tambah --agen koda --nama debug-api --tier dewa --dari T-003 --file skill.md
python3 scripts/belajar.py daftar --agen koda
python3 scripts/belajar.py daftar --status usulan     # antrean audit Saka
python3 scripts/belajar.py setujui --agen koda --nama debug-api   # Saka
python3 scripts/belajar.py naik-versi --agen koda --nama debug-api --catatan "..."
python3 scripts/belajar.py ubah-tier --agen koda --nama debug-api --tier dewa
```

Aturan: skill baru lahir sebagai `usulan` → **Saka mengaudit**
(aman? tidak duplikat? teruji? format benar? jujur?) → aktif. Agen boleh
berimprovisasi (gabung skill) dan berkoordinasi antar-agen untuk skill
gabungan (catat kontributor). Upgrade tier hanya atas penilaian Saka.

## Protokol dispatch (untuk Komandan/Hermes) — model merge

Agen-agen tim dilebur ke sub-agent native Hermes via `delegate_task`.
Komandan (Hermes, sebagai orchestrator) tidak menyalin prompt manual —
ia memakai `scripts/delegasikan.py`:

1. **Nilai dulu.** Tugas kecil → kerjakan sendiri. Tugas besar →
   delegasikan ke Nara untuk dipecah. **User menyapa agen langsung?**
   (`"koda, buatkan..."`, `"@tara ..."`) → rute langsung ke agen itu
   via `rute.py` — agen menerima perintah mentah dan menerjemahkannya
   mandiri. User bicara bebas? `rute.py "<perintah>"` menebak agen
   dari kata kunci (atau batch paralel bila multi-agen).
2. **Bangun & jalankan panggilan.** Untuk tiap tugas:
   ```bash
   python3 scripts/delegasikan.py <agen> --tugas <ID> [--latar]
   ```
   Salin kode `delegate_task(...)` yang dihasilkan ke `execute_code`.
   Butuh paralel? Satu panggilan batch:
   ```bash
   python3 scripts/delegasikan.py --batch "koda:T-002,raka:T-001" [--latar]
   ```
3. **Agen bekerja mandiri & paralel.** Tiap sub-agent lahir dengan
   konteks terisolasi + prompt perannya + daftar perangkat yang boleh
   dipakai (ditulis sebagai panduan di dalam `context`, karena
   `delegate_task` asli tidak punya argumen `toolsets` — toolset anak
   diturunkan dari role/depth), menjalankan
   siklusnya sendiri (ambil → kerjakan → cek-sendiri → selesai).
   Hanya ringkasan akhir yang kembali ke konteks Komandan.
   Mode `--latar` (background): hasil masuk sebagai pesan baru saat
   sub-agent selesai — Komandan bisa lanjut kerja lain.
4. **Verifikasi.** Tugas kode → panggil Vera
   (`delegasikan.py vera --tugas <ID>`).
5. **Audit.** Tugas penting → panggil Saka
   (`delegasikan.py saka --tugas <ID> --tujuan "Audit T-00X"`),
   lalu Saka menjalankan `tim.py audit` dan memberi vonis.
   Gagal → tugas dibuka lagi, pemilik wajib perbaiki.
6. **Rangkum.** Komandan merangkum semua hasil ke pengguna dalam satu
   jawaban rapi — jangan menumpahkan log mentah tiap agen.

### Vera vs Saka (untuk Komandan)

- **Vera** = verifikasi teknis, khusus tugas kode ("test lolos?").
- **Saka** = audit proses & mutu, untuk semua agen ("apakah ia mengikuti
  aturannya? apakah laporannya jujur?"). Jangan pakai satu untuk
  menggantikan yang lain.

## Aturan keselamatan (WAJIB)

1. **Paralelisme realistis.** Hermes menjalankan maksimal 3 sub-agent
   konkuren secara default (`delegation.max_concurrent_children`,
   bisa dinaikkan di `config.yaml`, tanpa batas keras). Papan tugas
   adalah antreannya — tugas ke-4+ menunggu sampai ada slot kosong.
   Jangan kirim batch raksasa sekaligus.
2. **Agen pekerja tidak mendelegasikan lagi.** Kalau stuck, lapor ke
   Komandan — tidak boleh ada rantai delegasi tanpa ujung.
3. **Batas putaran:** satu tugas yang dikembalikan >2 kali (mis.
   Vera menolak kerja Koda 3x) → hentikan, laporkan ke pengguna,
   minta arahan. Jangan loop tanpa akhir.
4. Aturan persetujuan `SOUL.md` tetap berlaku untuk SEMUA agen:
   aksi tak-terbalikkan (hapus, kirim, ubah sistem) wajib konfirmasi
   pengguna — tidak peduli agen mana yang mengusulkan.
5. Setiap agen hanya boleh memakai skill sesuai perannya
   (lihat tabel di `AGEN.md`). Koda tidak meriset web, Raka tidak
   menulis kode — kalau butuh, minta Komandan.
6. **Aturan Komando Mutlak** (lihat `AGEN.md`): setiap perintah/arahan
   Komandan adalah perintah pasti — terima, terjemahkan, eksekusi,
   tidak dapat ditolak. **Saka** menegakkannya: ia memastikan setiap
   instruksi/arahan user diperlakukan sebagai perintah mutlak oleh
   setiap agen (penolakan/penghindaran/penundaan/pelimpahan liar/
   pengecilan perintah = pelanggaran komando → vonis `gagal`).
   Pengecualian hanya untuk aturan keselamatan & mutu pack.
7. **Aturan Global Tim** (lihat `AGEN.md`): anti-karang (fakta wajib
   bukti, inferensi dilabeli `[ASUMSI]`), format laporan standar
   (apa+bukti+gagal, maks ~15 baris), Definition of Done
   (hasil+bukti+batas), papan = satu-satunya sumber kebenaran,
   interupsi prioritas `mendesak`, dan review kinerja berkala Saka.

**Review berkala:** setelah Hermes terinstal, buat cron mingguan untuk
Saka — mis. `laporan-kinerja` tiap Senin pagi, hasilnya dirangkum
Komandan ke user. Ini yang membuat akuntabilitas agen terukur terus.

## Batas jujur

- Peleburan ini nyata di sisi paket: definisi agen (`agen/*.json`),
  prompt peran (`peran/*.md`), dan pembangun panggilan
  (`scripts/delegasikan.py`, outputnya tervalidasi sintaks Python dan
  sesuai API `delegate_task`). Eksekusinya terjadi di Hermes yang
  terinstal di mesin pengguna — di sanalah `delegate_task` benar-benar
  melahirkan sub-agent.
- Sub-agent bersifat process-local: kalau proses Hermes mati, sub-agent
  yang background ikut hilang. Untuk kerja yang harus tahan restart,
  pakai `cronjob` atau `terminal(background=True)`.
- Kualitas tiap agen = kualitas model LLM yang dipakai Hermes.
  Peran + daftar perangkat memberi fokus dan batas, bukan kepintaran baru.
