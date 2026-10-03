# Template Skill Hermes

Salin folder ini sebagai titik awal setiap kali membuat skill baru:

```bash
cp -r skill-template nama-skill-baru
```

Lalu edit tiga hal:

1. **SKILL.md** — ganti nama, deskripsi, "kapan dipakai", dan cara pakai.
   Tulis untuk agen lain yang akan membacanya: kapan skill ini relevan,
   perintah apa yang tersedia, dan aturan keselamatan apa yang berlaku.
2. **scripts/** — taruh script yang melakukan kerja nyata (Python/Bash).
   Usahakan tanpa dependensi di luar bawaan sistem agar mudah dipasang.
3. Uji manual dulu dari terminal sebelum dipakai lewat agen.

Struktur baku (format agentskills.io):

```
nama-skill/
├── SKILL.md            # wajib: identitas + instruksi untuk agen
└── scripts/
    └── aksi.py         # kerja nyata
```

Contoh SKILL.md minimal:

```markdown
# Skill: nama-skill

Satu paragraf: apa yang dilakukan skill ini dan kenapa ada.

## Kapan dipakai

- Contoh ucapan pengguna yang memicu skill ini
- Contoh lainnya

## Cara pakai

```bash
python3 scripts/aksi.py --contoh nilai
```

## Aturan keselamatan

1. Apa yang boleh langsung jalan
2. Apa yang butuh konfirmasi dulu
```
