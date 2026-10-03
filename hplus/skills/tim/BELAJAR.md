# Sistem Belajar Tim hplus

Setiap agen **wajib belajar skill baru dan menyimpannya**. Skill bukan
hafalan mati — ia tumbuh dari pengalaman tugas, bisa diimprovisasi,
dikoordinasikan antar-agen, di-upgrade, dan diawasi Saka.

Ini adalah implementasi pack-level dari learning loop native Hermes
("Autonomous skill creation after complex tasks. Skills self-improve
during use") — dibuat eksplisit agar berjalan disiplin, bukan kebetulan.

## Kapan agen belajar

1. **Setelah tugas kompleks selesai** — ekstrak teknik yang berhasil
   menjadi skill yang bisa dipakai ulang.
2. **Setelah 2x gagal** — kegagalan adalah bahan skill ("pelajaran").
3. **Saat pola berulang** — teknik yang dipakai 3x+ layak diabadikan.

## Format skill yang disimpan

File: `pengetahuan/<agen>/<nama-skill>.md`

```markdown
# Skill: <nama>
Agen: <nama-agen> | Tier: <dasar/khusus/dewa/tambahan> | Versi: 1
Dari tugas: <T-00X / "-"> | Status: <usulan/aktif/nonaktif>
Diperbarui: <YYYY-MM-DD>

## Deskripsi
## Kapan dipakai
## Langkah
## Contoh
## Batasan
```

## Alur hidup skill

```
belajar → USULAN → audit Saka → AKTIF → dipakai → UPGRADE → ...
                                        ↘ usang → NONAKTIF
```

1. Agen menulis file skill + mendaftar via `scripts/belajar.py tambah`
   → status `usulan`.
2. **Saka mengaudit** (lihat "Pengawasan skill" di bawah) →
   `belajar.py setujui` → status `aktif`. Ditolak → perbaiki & ajukan lagi.
3. Dipakai di tugas nyata → disempurnakan → `naik-versi` (v1→v2...).
4. Terbukti ampuh berulang → `ubah-tier` naik (khusus→dewa) atas penilaian Saka.
5. Usang / terbukti buruk → `nonaktif` (riwayat tetap tersimpan).

## Improvisasi

Agen boleh **menggabungkan skill yang ada** menjadi teknik baru.
Wajib catat asal-usulnya di file skill ("Diturunkan dari: X + Y").
Improvisasi yang belum teruji di tugas nyata = tier `tambahan` dulu,
naik tier setelah terbukti.

## Koordinasi antar-agen (skill gabungan)

Skill yang butuh dua peran (mis. Koda+Vera: "perbaiki-dan-verifikasi-loop")
dibuat via tugas koordinasi di papan:

1. Komandan buat tugas untuk kedua agen (atau satu agen mengusulkan).
2. Kedua agen mengerjakan bagiannya, hasilnya digabung jadi satu file skill.
3. File mencatat kedua kontributor: `Kontributor: koda, vera`.
4. Saka audit → aktif. Skill gabungan tercatat di registry kedua agen.

## Pengawasan Saka atas skill

Saka mengawasi **semua** penambahan, update, dan upgrade skill tiap agen.
Checklist audit skill:

- [ ] **Aman** — tidak melanggar batas keras peran / aturan keselamatan.
- [ ] **Tidak duplikat** — belum ada skill setara di agen itu.
- [ ] **Teruji** — lahir dari tugas nyata (bukan teori), atau ditandai eksperimental.
- [ ] **Format benar** — header lengkap, langkah konkret, ada batasan.
- [ ] **Jujur** — klaim kemampuan sesuai bukti, tidak melebih-lebihkan.
- [ ] **Upgrade beralasan** — naik versi/tier ada catatan perubahannya.

Saka boleh: menolak usulan, menurunkan tier, menonaktifkan skill yang
terbukti buruk, dan memerintahkan perbaikan. Semua via `belajar.py`.

## Perintah

```bash
python3 scripts/belajar.py tambah --agen koda --nama debug-api \
  --tier dewa --dari T-003 --file skill.md
python3 scripts/belajar.py daftar --agen koda
python3 scripts/belajar.py daftar --status usulan      # antrean audit Saka
python3 scripts/belajar.py setujui --agen koda --nama debug-api
python3 scripts/belajar.py naik-versi --agen koda --nama debug-api \
  --catatan "tambah langkah git-bisect"
python3 scripts/belajar.py ubah-tier --agen koda --nama debug-api --tier dewa
python3 scripts/belajar.py nonaktif --agen koda --nama debug-api
python3 scripts/belajar.py info --agen koda --nama debug-api
```
