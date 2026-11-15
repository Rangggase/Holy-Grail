"""Laporan & analitik untuk dasbor admin. Semua angka dihitung dari data transaksi nyata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.engine import Engine

# Batas total belanja pelanggan (rupiah) -> tingkat. Urut dari tertinggi.
SEGMENT_TIERS: tuple[tuple[str, int, str], ...] = (
    ("Diamond", 10_000_000, "Layanan personal & akses awal menu baru"),
    ("Platinum", 4_500_000, "Paket bundling eksklusif"),
    ("Gold", 3_000_000, "Promo diskon berkala"),
    ("Silver", 1_000_000, "Voucher reguler"),
    ("Bronze", 0, "Penawaran beli 1 gratis 1 untuk kunjungan berikut"),
)

_SALES_SQL = text(
    """
    SELECT t.trx_id, t.created_at, t.payment_method, t.weather, t.group_size, t.time_of_day,
           c.customer_id, c.name AS customer_name,
           m.menu_id, m.menu_name, m.category,
           i.qty, i.unit_price, i.subtotal
    FROM transactions t
    JOIN customers c ON c.customer_id = t.customer_id
    JOIN transaction_items i ON i.trx_id = t.trx_id
    JOIN menu m ON m.menu_id = i.menu_id
    WHERE t.created_at >= :start AND t.created_at < :end
    """
).bindparams(bindparam("start", type_=DateTime), bindparam("end", type_=DateTime))


@dataclass(frozen=True)
class Kpis:
    revenue: int
    transactions: int
    items_sold: int
    avg_basket: int
    best_seller: str


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())


def sales_lines(engine: Engine, start: date, end: date) -> pd.DataFrame:
    """Satu baris per item transaksi dalam rentang tanggal (inklusif)."""
    s, e = _bounds(start, end)
    with engine.connect() as conn:
        df = pd.read_sql(_SALES_SQL, conn, params={"start": s, "end": e})
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def kpis(lines: pd.DataFrame) -> Kpis:
    if lines.empty:
        return Kpis(0, 0, 0, 0, "-")
    trx = lines.drop_duplicates("trx_id")["trx_id"].nunique()
    revenue = int(lines["subtotal"].sum())
    best = lines.groupby("menu_name")["qty"].sum().sort_values(ascending=False)
    return Kpis(revenue, int(trx), int(lines["qty"].sum()), revenue // trx, str(best.index[0]))


def daily_sales(lines: pd.DataFrame) -> pd.DataFrame:
    if lines.empty:
        return pd.DataFrame(columns=["tanggal", "omzet", "transaksi"])
    d = lines.assign(tanggal=lines["created_at"].dt.normalize())
    out = d.groupby("tanggal").agg(omzet=("subtotal", "sum"), transaksi=("trx_id", "nunique")).reset_index()
    return out


def hourly_sales(lines: pd.DataFrame) -> pd.DataFrame:
    base = pd.DataFrame({"jam": range(24)})
    if lines.empty:
        return base.assign(omzet=0, transaksi=0)
    d = lines.assign(jam=lines["created_at"].dt.hour)
    g = d.groupby("jam").agg(omzet=("subtotal", "sum"), transaksi=("trx_id", "nunique")).reset_index()
    return base.merge(g, on="jam", how="left").fillna(0).astype({"omzet": int, "transaksi": int})


def top_menu(lines: pd.DataFrame, *, drinks: bool, n: int = 5) -> pd.DataFrame:
    if lines.empty:
        return pd.DataFrame(columns=["menu", "terjual", "omzet"])
    mask = lines["category"] == "Minuman"
    d = lines[mask] if drinks else lines[~mask]
    g = d.groupby("menu_name").agg(terjual=("qty", "sum"), omzet=("subtotal", "sum")).reset_index()
    return g.rename(columns={"menu_name": "menu"}).sort_values(["terjual", "omzet"], ascending=False).head(n).reset_index(drop=True)


def segment_for(total_spend: int) -> str:
    for name, minimum, _ in SEGMENT_TIERS:
        if total_spend >= minimum:
            return name
    return SEGMENT_TIERS[-1][0]


def customer_segments(lines: pd.DataFrame) -> pd.DataFrame:
    cols = ["customer_id", "nama", "total_belanja", "jumlah_transaksi", "segmen"]
    if lines.empty:
        return pd.DataFrame(columns=cols)
    g = lines.groupby(["customer_id", "customer_name"]).agg(
        total_belanja=("subtotal", "sum"), jumlah_transaksi=("trx_id", "nunique")
    ).reset_index().rename(columns={"customer_name": "nama"})
    g["segmen"] = g["total_belanja"].astype(int).map(segment_for)
    return g[cols]


def transaction_table(lines: pd.DataFrame) -> pd.DataFrame:
    """Tabel riwayat siap tampil/ekspor (kolom berbahasa Indonesia)."""
    if lines.empty:
        return pd.DataFrame()
    d = lines.sort_values(["created_at", "trx_id"], ascending=[False, False])
    return pd.DataFrame(
        {
            "No. Transaksi": d["trx_id"],
            "Waktu": d["created_at"].dt.strftime("%Y-%m-%d %H:%M"),
            "Pelanggan": d["customer_name"],
            "Menu": d["menu_name"],
            "Kategori": d["category"],
            "Jumlah": d["qty"],
            "Harga Satuan": d["unit_price"],
            "Subtotal": d["subtotal"],
            "Pembayaran": d["payment_method"],
        }
    ).reset_index(drop=True)


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def to_safe_csv(df: pd.DataFrame) -> bytes:
    """CSV UTF-8 (BOM agar Excel membaca benar). Sel teks berawalan = + - @ diberi apostrof (cegah CSV/formula injection)."""
    safe = df.copy()
    for col in safe.columns:
        if safe[col].dtype == object or str(safe[col].dtype).startswith("str"):
            safe[col] = safe[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(_FORMULA_PREFIXES) else v)
    return safe.to_csv(index=False).encode("utf-8-sig")
