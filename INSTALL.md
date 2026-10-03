# hplus agent — paket lengkap (Hermes + kustomisasi)

Satu bundel utuh: **Hermes asli** (dari GitHub NousResearch, MIT) +
**paket hplus v24** yang sudah diletakkan di tempat yang benar.
Bukan file lepas — tinggal install.

## Isi bundel

| Folder | Isi |
|---|---|
| `hermes-src/` | Source Hermes asli (referensi; installer resmi yang dipakai) |
| `hplus/skills/` | 12 skill hplus: `tim` (7 agen + Nara..Ari), `browser`, `kantor`, `koding`, `wifilab`, `sinyal`, `pasar`, `strategi-teruji`, `web`, `arsip`, `tujuan` |
| `hplus/SOUL.md` | Kepribadian Indonesia milik Ari |
| `hplus/config-snippet.yaml` | Tambahan config opsional |
| `install.sh` | Installer otomatis (VPS Linux) |

Versi upstream tercatat di `VERSION.txt`.

## Cara pasang (VPS)

```bash
unzip hplus-agent-full-v24.zip
cd hplus-agent-full
bash install.sh
```

Lalu:

1. `hermes model` — pilih provider & model LLM
2. `export LLM_API_KEY=...` — isi di VPS langsung, **jangan** lewat chat
3. `hermes` — coba: `tampilkan status tim`
4. Dashboard: `python3 ~/.hermes/skills/kantor/server.py`

## Yang berubah dari pack lama (v24)

- Snippet `delegasikan.py` kini 100% cocok dengan signature
  `delegate_task` Hermes asli (tanpa argumen `toolsets` — daftar
  perangkat ditulis sebagai panduan di dalam `context`).
- Skill `tim` memakai memori (`ingat.py`), konteks tim, dan pelajaran
  otomatis dari audit gagal.

## Catatan jujur

- Bundel ini **belum diinstall/dijalankan** di mesin pembuatnya —
  install + uji end-to-end dilakukan di VPS-mu via `install.sh`.
- Lisensi Hermes: MIT (NousResearch). Paket hplus: milik Ari.
- Dashboard Kantor hplus tidak punya login bawaan — jangan dibuka
  ke publik tanpa password/reverse proxy.
