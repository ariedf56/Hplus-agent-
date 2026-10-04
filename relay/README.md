# Relay hplus 🔌

Jembatan remote: Muse mengirim perintah lewat `inbox.json`,
script `relay.sh` di Termux mengeksekusi dan menulis hasil ke `outbox/`.

- Hasil di `outbox/` dihapus Muse setelah dibaca (tidak menumpuk, tidak publik lama).
- Token yang dipakai: fine-grained, hanya Contents read+write di repo ini.
- Matikan relay dengan Ctrl+C; cabut tokennya di github.com/settings/tokens setelah selesai.
