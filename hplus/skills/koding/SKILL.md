# Skill: koding

Asisten koding Hermes — baca, tulis, ubah, jalankan, dan uji kode langsung
dari percakapan. **100% di dalam paket**: tanpa install tambahan, tanpa
API key baru. Penalaran kode dilakukan oleh otak LLM Hermes sendiri;
skill ini menyediakan "tangan" yang aman dan terstruktur.

## Kapan dipakai

Pakai skill ini ketika pengguna meminta hal yang berkaitan dengan kode:

- "buatkan program X" / "tulis script untuk Y"
- "perbaiki bug di file Z" / "ada error, tolong debug"
- "jelaskan isi project ini" / "project ini strukturnya gimana?"
- "jalankan programnya" / "coba test-nya lolos nggak?"
- "review perubahan kodeku"

## Cara pakai

Semua aksi lewat `python3 scripts/koding.py` dari folder skill ini.
Folder kerja default: **MODE LELUASA** — seluruh filesystem (`/`),
baca/tulis/eksekusi bebas di seluruh VPS. Batasi via `KODING_ROOT`
(mis. `~` atau `~/proyek`) bila ingin memperketat. Path traversal
(`../`, symlink keluar root) tetap ditolak otomatis.

```bash
python3 scripts/koding.py pindai myapp              # petakan struktur proyek
python3 scripts/koding.py pindai myapp --dalam 2    # tree lebih dangkal
python3 scripts/koding.py baca myapp/main.py        # baca file + nomor baris
python3 scripts/koding.py baca myapp/main.py --dari 10 --sampai 30
python3 scripts/koding.py tulis myapp/bot.py --isi "..."   # file baru
echo "..." | python3 scripts/koding.py tulis myapp/bot.py # via pipe
python3 scripts/koding.py ubah myapp/main.py --cari "lama" --ganti "baru"
python3 scripts/koding.py ubah myapp/main.py --cari "x" --ganti "y" --semua
python3 scripts/koding.py jalankan myapp -- python3 main.py
python3 scripts/koding.py uji myapp                 # deteksi & jalankan test
python3 scripts/koding.py kembalikan myapp/main.py  # undo dari cadangan .bak
```

Pemetaan bahasa natural → perintah:

| Pengguna bilang | Jalankan |
|---|---|
| jelaskan / struktur project ini | `pindai <dir>` dulu, lalu `baca` file kuncinya |
| buatkan program / script baru | `tulis <file> --isi ...` |
| perbaiki / ubah bagian kode | `baca` dulu → `ubah --cari ... --ganti ...` |
| ada error / debug | `baca` file error → `jalankan` untuk reproduksi → `ubah` |
| jalankan / coba programnya | `jalankan <dir> -- <perintah>` |
| test lolos? | `uji <dir>` |
| review kodeku | `pindai` + `baca` file yang diubah, rangkum perubahan |
| batalkan / undo perubahan | `kembalikan <file>` |

## Alur kerja yang benar (WAJIB)

1. **`pindai` dulu** sebelum mengerjakan proyek yang belum dikenal.
2. **`baca` file** sebelum mengubahnya — jangan menebak isi file.
3. **`ubah`** membuat cadangan `.bak` + menampilkan diff otomatis.
   Tunjukkan diff ke pengguna, jangan menumpahkan seluruh file.
4. **`uji`** (atau `jalankan`) setelah mengubah kode — pastikan tidak rusak.
5. Kalau gagal, **`kembalikan`** lalu coba pendekatan lain.

## Aturan keselamatan (WAJIB)

1. **Mode leluasa.** Default `KODING_ROOT` = `/` (seluruh filesystem
   VPS). Script tetap menolak path traversal (`../`, symlink keluar
   root), membuat cadangan `.bak` tiap ubah/timpa, dan memfilter
   perintah berbahaya di `jalankan`. Mode leluasa = tanggung jawab
   penuh: perintahkan dengan path yang presisi.
2. **Tulis/ubah selalu bisa di-undo.** Cadangan `.bak` dibuat otomatis
   setiap kali file ditimpa/diubah.
3. **`jalankan` menolak perintah berbahaya** (`rm -rf /`, fork bomb,
   `mkfs`, `dd ke /dev/`, shutdown, dsb) kecuali flag `--saya-yakin`.
   Flag itu HANYA boleh dipakai setelah pengguna menyetujui eksplisit
   di chat — sesuai aturan persetujuan di `SOUL.md`.
4. **Perintah yang mengubah/menghapus di luar proyek** (install paket
   sistem, hapus file di luar folder kerja) → minta konfirmasi dulu,
   jelaskan apa yang akan terjadi.
5. **Perintah baca** (`pindai`, `baca`) aman dan boleh langsung dijalankan.
6. Jangan menampilkan isi file kredensial (`.env`, `*key*`, `*token*`,
   `*secret*`) apa adanya ke pengguna kecuali ia memintanya eksplisit.

## Batas jujur skill ini

- Ini **bukan** OpenCode/Cursor: tidak ada LSP, tidak ada multi-agent,
  tidak ada analisis semantik mendalam. Ini toolkit kerja yang pragmatis.
- **Kualitas penalaran kode = kualitas model LLM yang dipakai Hermes.**
  Skill ini tidak menambah "kepintaran", hanya memberi tangan yang aman.
- `uji` mendeteksi pytest/unittest/npm/go test secara sederhana; proyek
  dengan setup test eksotis mungkin perlu perintah `jalankan` manual.
- Skill ini tidak menggantikan `git` — untuk version control serius,
  tetap pakai git via `jalankan` (atau minta pengguna menggunakannya).
