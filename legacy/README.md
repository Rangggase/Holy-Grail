# Arsip kode lama (v4, Streamlit + PostgreSQL + TensorFlow)

Hanya untuk referensi sejarah — **tidak diimpor** oleh aplikasi baru.
- `app_v4.py`, `admin_view.py`, `kasir_view.py`: versi prototipe awal.
- `models/*.pkl|*.h5`: model NCF/KMeans lama. File pickle dapat mengeksekusi kode saat dimuat; **jangan dimuat dari sumber tak tepercaya**.
  Aplikasi baru memakai rekomendasi berbasis aturan + riwayat transaksi (lihat `holygrail/services/recommender.py`).
