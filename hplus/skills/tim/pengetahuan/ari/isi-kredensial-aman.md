# Isi kredensial dengan aman 🔑

1. `kredensial.py cek --label <label>` — pastikan tercatat.
2. `browser.py buka <situs>` — verifikasi domain PERSIS seperti tercatat.
3. `kredensial.py isi --label <label> --identitas-sel <sel> --rahasia-sel <sel> [--kirim-sel <sel>]`
   → rahasia mengalir langsung ke form, tidak pernah tampil.
4. Verifikasi login berhasil (dashboard / tombol logout muncul).
5. Lapor TANPA rahasia: "login <label> berhasil ✅".

Palsu/phishing: URL beda, redirect asing, tampilan aneh → BERHENTI + lapor ancaman.
