# Holy Grail POS

Aplikasi **kasir (Point of Sale) dan manajemen restoran** berbahasa Indonesia, dibangun dengan Streamlit, SQLAlchemy, dan SQLite/PostgreSQL. Proyek portofolio mahasiswa Sistem Informasi yang menunjukkan perancangan basis data relasional, logika transaksi yang aman, dan antarmuka yang dirancang untuk dipakai di tablet kasir.

> Data demo bersifat **fiktif** (dibangkitkan oleh `scripts/seed_demo.py`). Daftar menu (70 item) berasal dari prototipe awal proyek ini.

## Masalah & solusi

| Masalah di restoran kecil | Solusi di aplikasi ini |
|---|---|
| Kasir mencatat manual, total & kembalian sering salah | Total dihitung di server dari harga di database; kembalian otomatis; nota langsung tampil |
| Stok menu tidak terpantau, pesanan melebihi stok | Stok berkurang atomik saat bayar (`UPDATE … WHERE stock >= qty`); pembayaran ditolak bila stok kurang; peringatan stok menipis |
| Harga berubah, laporan lama ikut berubah | Harga disalin (*snapshot*) ke setiap baris transaksi |
| Tidak tahu jam sibuk, menu terlaris, dan pelanggan terbaik | Dasbor admin: omzet harian, jam sibuk, menu terlaris, segmentasi pelanggan, ekspor CSV |
| Kasir bingung merekomendasikan menu | Saran menu berbasis aturan (cuaca, rombongan) dan riwayat penjualan, lengkap dengan alasannya |

## Fitur

**Kasir** — pencarian/pendaftaran pelanggan otomatis, konteks pesanan (cuaca, rombongan, waktu), saran menu, buku menu per kategori, keranjang, pembayaran Tunai/QRIS/Debit-Kredit (tombol uang cepat), nota + unduh `.txt`, klik ganda tidak membuat transaksi ganda.

**Admin** — filter periode; KPI; grafik omzet harian & jam sibuk; menu terlaris makanan/minuman; segmentasi pelanggan (Diamond → Bronze); tambah/ubah menu; penyesuaian stok dengan riwayat; tabel transaksi + ekspor CSV yang aman dari *formula injection*.

**Keamanan** — password di-hash `scrypt` (tanpa password di kode), login berperan (admin/kasir), pembatas percobaan login per sesi, validasi input ketat, query terparameter, HTML di-*escape*, pesan error ramah tanpa detail teknis, rahasia hanya dari `.env`.

> Catatan jujur: ini aplikasi demo untuk jaringan lokal. Pembatas login bersifat per sesi browser (bukan per IP), belum ada HTTPS/2FA/audit log akun, dan SQLite hanya cocok untuk satu toko. Lihat [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) bagian *Batasan*.

## Mulai cepat

Prasyarat: Python 3.11 atau lebih baru. Diuji lokal pada Python 3.13.9 dengan streamlit 1.67, SQLAlchemy 2.1, pandas 3.1, plotly 7.1. Workflow CI untuk Python 3.11–3.13 sudah disiapkan di `.github/workflows/ci.yml` tetapi belum pernah dijalankan.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows. Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # lalu isi ADMIN_PASSWORD dan KASIR_PASSWORD (min. 8 karakter, huruf+angka)
python -m scripts.init_db --demo  # buat skema, 70 menu, 2 akun, ±6.000 transaksi fiktif
streamlit run app.py
```

Buka <http://localhost:8501> dan masuk dengan akun dari `.env` (username `admin` atau `kasir`). Jika `ADMIN_PASSWORD`/`KASIR_PASSWORD` dikosongkan, `init_db` membuat password acak dan mencetaknya **sekali** (di GitHub Codespaces, lihat log pembuatan container).

Opsi `init_db`: `--demo` (data demo), `--reset` (hapus semua tabel lalu buat ulang).

## Membuka database di DBeaver

Database default adalah **SQLite satu file**: `data/holygrail.db` (dibuat oleh `init_db`, tidak di-commit).

1. Jalankan `python -m scripts.init_db --demo` agar file database ada.
2. DBeaver → **Database → New Database Connection** → pilih **SQLite** → *Next*.
3. Isi **Path** dengan lokasi file, misalnya `D:\new another projectc\Holy-Grail\data\holygrail.db` (atau klik *Open…* lalu pilih file).
4. Username/password **dikosongkan** (SQLite tidak memakainya). Jika diminta mengunduh *driver* SQLite, klik **Download**.
5. **Test Connection** → **Finish**. Buka *Tables* untuk melihat 6 tabel, dan **ER Diagram** (klik kanan database → *View Diagram*) untuk melihat relasi.

Parameter ringkas:

| Parameter | Nilai |
|---|---|
| Driver | SQLite |
| Path | `<folder proyek>/data/holygrail.db` |
| User / Password | kosong |
| Foreign key | aktif di aplikasi; di DBeaver aktifkan lewat `PRAGMA foreign_keys = ON;` bila Anda mengedit data manual |

Tutup aplikasi (atau hindari menulis bersamaan) saat mengedit data langsung di DBeaver. Skema lengkap: [docs/schema.sql](docs/schema.sql).

**Memakai PostgreSQL:** isi `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/holygrail` di `.env`, jalankan `pip install psycopg2-binary`, lalu `python -m scripts.init_db --demo`. Di DBeaver pilih driver **PostgreSQL** dengan host/port/database yang sama.

## Hasil pengujian (dijalankan pada 16 Nov 2026, Python 3.13.9, Windows)

`pytest --cov=holygrail --cov=scripts` → **87 tes lulus, 0 gagal**, cakupan baris **91%**.

| Jenis | Jumlah | Yang diverifikasi |
|---|---|---|
| Unit | 50 | validasi & sanitasi input, hash/verifikasi password, pembatas login, aturan rekomendasi, kontras warna WCAG AA tema |
| Integrasi | 30 | checkout (total, kembalian, stok, rollback, idempotensi, 6 checkout bersamaan pada stok 3), constraint database (PK/FK/UNIQUE/CHECK), autentikasi, stok, laporan & segmentasi, ekspor CSV aman, `init_db` idempoten |
| E2E | 7 | `app.py` dijalankan lewat Streamlit AppTest: login gagal & kunci, alur penjualan kasir sampai nota, batas stok, pembatasan akses admin, dasbor admin & penyesuaian stok, logout |

Keterbatasan pengujian: E2E memakai `streamlit.testing` (tanpa browser sungguhan). Tampilan visual (desktop 1280px dan tablet 768px) diperiksa manual di browser; belum ada tes regresi visual otomatis.

## Struktur folder

```
app.py                  entry point Streamlit
holygrail/
  config.py db.py security.py validation.py errors.py
  services/             logika bisnis murni (auth, menu, customers, checkout, reports, recommender)
  ui/                   theme (design system), components, login, kasir, admin
scripts/                init_db.py, seed_demo.py
data/seed/menu.csv      seed menu
docs/                   ARCHITECTURE.md, schema.sql
tests/                  unit/ integration/ e2e/
legacy/                 arsip prototipe lama (tidak dipakai)
```

## Tentang perubahan besar (v2)

Prototipe awal (Streamlit + PostgreSQL + model TensorFlow/pickle, password admin tertanam di kode) dirombak total: skema relasional dengan constraint, layanan bisnis yang diuji, autentikasi berperan, dan UI baru. Model TensorFlow/pickle lama **tidak lagi dipakai** (berat, dan file pickle tidak aman dimuat); diganti rekomendasi berbasis aturan yang transparan. Arsip ada di `legacy/`, tag `backup/pre-revamp` menyimpan kondisi awal.

## Lisensi

Belum ada berkas lisensi; semua hak dipegang pemilik repositori sampai lisensi ditambahkan.
