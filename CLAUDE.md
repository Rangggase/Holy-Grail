# CLAUDE.md — Holy Grail POS

Aplikasi kasir (POS) & manajemen restoran berbasis **Streamlit + SQLAlchemy**. Portofolio mahasiswa Sistem Informasi.
Semua teks antarmuka dan pesan error untuk pengguna memakai **Bahasa Indonesia** formal-ramah.

## Arsitektur (berlapis, satu arah: UI → services → db)

```
app.py                  Entry point Streamlit: router halaman + guard peran
holygrail/
  config.py             Baca setting dari environment/.env (satu-satunya tempat os.environ dibaca)
  db.py                 Skema SQLAlchemy Core + engine factory (SQLite default, PostgreSQL via DATABASE_URL)
  security.py           Hash password (scrypt), verifikasi, pembatas percobaan login
  validation.py         Validasi & sanitasi input (nama, harga, qty, uang)
  errors.py             Exception domain (ValidationError, StockError, ...) berpesan Indonesia
  services/             Logika bisnis MURNI — tanpa import streamlit
    auth.py  menu.py  customers.py  checkout.py  reports.py  recommender.py
  ui/                   Semua kode Streamlit: theme.py (design system), components.py, login.py, kasir.py, admin.py
scripts/                init_db.py, seed_demo.py (CLI)
data/seed/menu.csv      Seed menu (70 item). Database hidup: data/holygrail.db (gitignored)
tests/                  unit/, integration/, e2e/ (streamlit AppTest)
legacy/                 Arsip kode & model lama (read-only, tidak diimpor)
docs/ARCHITECTURE.md
```

## Aturan wajib
1. **Layer**: `services/` tidak boleh `import streamlit`. `ui/` tidak boleh menulis SQL; panggil service.
2. **Uang** = integer rupiah. Jangan float. Format tampilan lewat `ui.components.rupiah()`.
3. **Harga selalu dibaca server-side dari DB** saat checkout dan disalin (snapshot) ke `transaction_items.unit_price`.
4. **Checkout atomik**: satu transaksi DB; stok dikurangi dengan `UPDATE ... WHERE stock >= :qty`; `idempotency_key` unik mencegah dobel submit.
5. **Rahasia** hanya dari `.env` (lihat `.env.example`). Jangan hardcode password/URL. Jangan commit `.env` atau `data/*.db`.
6. **Query selalu parameterized** (SQLAlchemy `text()` dengan bind param / Core). Tidak ada f-string SQL.
7. **HTML di `st.markdown(unsafe_allow_html=True)`** wajib melewati `html.escape` untuk data dari DB/input pengguna.
8. Pesan error ke pengguna: ramah, tanpa stack trace/SQL; detail teknis ke `logging`.
9. DB harus tetap bisa dibuka di DBeaver: SQLite file tunggal, FK aktif, constraint di level DB (bukan hanya aplikasi).
10. Rekomendasi menu = **aturan + riwayat transaksi** (bukan model ML). Jangan mengklaim "AI" di UI/README.

## Perintah
```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                  # lalu isi password
python -m scripts.init_db --demo                      # buat skema + seed menu + data demo + akun staf
streamlit run app.py
pytest                                                # unit + integrasi + e2e
```

## Gaya & desain
- Design system ada di `holygrail/ui/theme.py` (token warna/tipografi). Kontras teks ≥ WCAG AA (diuji di `tests/unit/test_theme_contrast.py`).
- Angka & harga: `font-variant-numeric: tabular-nums`. Target sentuh ≥ 44px (tablet kasir).
- Commit: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
