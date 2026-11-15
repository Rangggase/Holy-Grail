"""Skema database (SQLAlchemy Core) dan pembuat engine.

Default: SQLite satu file (`data/holygrail.db`) yang dapat langsung dibuka di DBeaver.
PostgreSQL didukung lewat `DATABASE_URL` — skema memakai tipe & constraint portabel.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

WEATHERS = ("Cerah", "Hujan")
GROUP_SIZES = ("Sendiri", "Keluarga")
TIMES_OF_DAY = ("Pagi", "Siang", "Sore", "Malam")
PAYMENT_METHODS = ("Tunai", "QRIS", "Debit/Kredit")
ROLES = ("admin", "kasir")
STOCK_REASONS = ("initial", "restock", "adjustment", "sale")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

staff = Table(
    "staff",
    metadata,
    Column("staff_id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(40), nullable=False, unique=True),
    Column("full_name", String(80), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(10), nullable=False),
    Column("is_active", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint(_in("role", ROLES), name="role_valid"),
    CheckConstraint("is_active IN (0, 1)", name="active_bool"),
    CheckConstraint("username = lower(username) AND length(username) >= 3", name="username_format"),
)

customers = Table(
    "customers",
    metadata,
    Column("customer_id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(60), nullable=False),
    # Kunci pencarian huruf kecil: mencegah pelanggan ganda ("Budi" vs "budi").
    Column("name_key", String(60), nullable=False, unique=True),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("length(trim(name)) >= 2", name="name_min_length"),
)

menu = Table(
    "menu",
    metadata,
    Column("menu_id", Integer, primary_key=True, autoincrement=True),
    Column("menu_name", String(80), nullable=False, unique=True),
    Column("category", String(40), nullable=False),
    Column("price", Integer, nullable=False),
    Column("stock", Integer, nullable=False, server_default="0"),
    Column("is_active", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("price > 0", name="price_positive"),
    CheckConstraint("stock >= 0", name="stock_non_negative"),
    CheckConstraint("is_active IN (0, 1)", name="active_bool"),
    Index("ix_menu_category", "category"),
)

transactions = Table(
    "transactions",
    metadata,
    Column("trx_id", Integer, primary_key=True, autoincrement=True),
    # Kunci idempoten: klik ganda / refresh tidak membuat transaksi ganda.
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("customer_id", Integer, ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False),
    Column("cashier_id", Integer, ForeignKey("staff.staff_id", ondelete="RESTRICT")),
    Column("created_at", DateTime, nullable=False),
    Column("weather", String(10), nullable=False),
    Column("group_size", String(10), nullable=False),
    Column("time_of_day", String(10), nullable=False),
    Column("payment_method", String(20), nullable=False),
    Column("total", Integer, nullable=False),
    Column("paid", Integer, nullable=False),
    Column("change_amount", Integer, nullable=False),
    CheckConstraint(_in("weather", WEATHERS), name="weather_valid"),
    CheckConstraint(_in("group_size", GROUP_SIZES), name="group_valid"),
    CheckConstraint(_in("time_of_day", TIMES_OF_DAY), name="time_valid"),
    CheckConstraint(_in("payment_method", PAYMENT_METHODS), name="payment_valid"),
    CheckConstraint("total > 0", name="total_positive"),
    CheckConstraint("paid >= total", name="paid_covers_total"),
    CheckConstraint("change_amount = paid - total", name="change_consistent"),
    Index("ix_transactions_created_at", "created_at"),
    Index("ix_transactions_customer", "customer_id"),
)

transaction_items = Table(
    "transaction_items",
    metadata,
    Column("item_id", Integer, primary_key=True, autoincrement=True),
    Column("trx_id", Integer, ForeignKey("transactions.trx_id", ondelete="CASCADE"), nullable=False),
    Column("menu_id", Integer, ForeignKey("menu.menu_id", ondelete="RESTRICT"), nullable=False),
    Column("qty", Integer, nullable=False),
    # Snapshot harga saat transaksi: perubahan harga menu tidak mengubah riwayat.
    Column("unit_price", Integer, nullable=False),
    Column("subtotal", Integer, nullable=False),
    CheckConstraint("qty > 0 AND qty <= 99", name="qty_range"),
    CheckConstraint("unit_price > 0", name="unit_price_positive"),
    CheckConstraint("subtotal = qty * unit_price", name="subtotal_consistent"),
    UniqueConstraint("trx_id", "menu_id", name="uq_items_trx_menu"),
    Index("ix_items_menu", "menu_id"),
)

stock_movements = Table(
    "stock_movements",
    metadata,
    Column("movement_id", Integer, primary_key=True, autoincrement=True),
    Column("menu_id", Integer, ForeignKey("menu.menu_id", ondelete="RESTRICT"), nullable=False),
    Column("delta", Integer, nullable=False),
    Column("reason", String(12), nullable=False),
    Column("note", Text),
    Column("staff_id", Integer, ForeignKey("staff.staff_id", ondelete="SET NULL")),
    Column("trx_id", Integer, ForeignKey("transactions.trx_id", ondelete="SET NULL")),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("delta <> 0", name="delta_nonzero"),
    CheckConstraint(_in("reason", STOCK_REASONS), name="reason_valid"),
    Index("ix_stock_movements_menu", "menu_id"),
)


def _prepare_sqlite_path(url: str) -> None:
    parsed = make_url(url)
    if parsed.drivername.startswith("sqlite") and parsed.database and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


def make_engine(url: str) -> Engine:
    """Buat engine. Untuk SQLite: aktifkan foreign key & busy timeout (PRAGMA)."""
    _prepare_sqlite_path(url)
    engine = create_engine(url, future=True, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - dipanggil driver
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

    return engine


def create_schema(engine: Engine) -> None:
    metadata.create_all(engine)
