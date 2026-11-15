"""Manajemen menu & stok."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import insert, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .. import db
from ..errors import NotFoundError, StockError, ValidationError
from ..validation import clean_category, clean_menu_name, parse_int, parse_price

LOW_STOCK_THRESHOLD = 10


def list_menu(engine: Engine, *, active_only: bool = True) -> pd.DataFrame:
    q = "SELECT menu_id, menu_name, category, price, stock, is_active FROM menu"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY category, menu_name"
    with engine.connect() as conn:
        return pd.read_sql(text(q), conn)


def add_menu(engine: Engine, *, name: str, category: str, price: object, stock: object = 0, staff_id: int | None = None) -> int:
    name, category = clean_menu_name(name), clean_category(category)
    price = parse_price(price)
    stock = parse_int(stock, field="Stok awal", minimum=0, maximum=100_000)
    try:
        with engine.begin() as conn:
            menu_id = int(
                conn.execute(insert(db.menu).values(menu_name=name, category=category, price=price, stock=stock)).inserted_primary_key[0]
            )
            if stock:
                conn.execute(
                    insert(db.stock_movements).values(
                        menu_id=menu_id, delta=stock, reason="initial", staff_id=staff_id, created_at=datetime.now()
                    )
                )
            return menu_id
    except IntegrityError:
        raise ValidationError(f"Menu '{name}' sudah ada.") from None


def update_menu(engine: Engine, menu_id: int, *, name: str, category: str, price: object, is_active: bool) -> None:
    name, category, price = clean_menu_name(name), clean_category(category), parse_price(price)
    try:
        with engine.begin() as conn:
            res = conn.execute(
                update(db.menu)
                .where(db.menu.c.menu_id == menu_id)
                .values(menu_name=name, category=category, price=price, is_active=1 if is_active else 0)
            )
            if res.rowcount == 0:
                raise NotFoundError("Menu tidak ditemukan.")
    except IntegrityError:
        raise ValidationError(f"Menu '{name}' sudah ada.") from None


def adjust_stock(engine: Engine, menu_id: int, delta: int, *, reason: str, staff_id: int | None, note: str = "") -> int:
    """Ubah stok secara atomik. Mengembalikan stok baru. Stok tidak boleh negatif."""
    if reason not in ("restock", "adjustment"):
        raise ValidationError("Alasan penyesuaian stok tidak valid.")
    delta = parse_int(delta, field="Perubahan stok", minimum=-100_000, maximum=100_000)
    if delta == 0:
        raise ValidationError("Perubahan stok tidak boleh nol.")
    with engine.begin() as conn:
        res = conn.execute(
            update(db.menu).where(db.menu.c.menu_id == menu_id, db.menu.c.stock + delta >= 0).values(stock=db.menu.c.stock + delta)
        )
        if res.rowcount == 0:
            exists = conn.execute(select(db.menu.c.menu_id).where(db.menu.c.menu_id == menu_id)).first()
            if not exists:
                raise NotFoundError("Menu tidak ditemukan.")
            raise StockError("Stok tidak boleh menjadi negatif.")
        conn.execute(
            insert(db.stock_movements).values(
                menu_id=menu_id, delta=delta, reason=reason, note=(note or "").strip()[:200] or None,
                staff_id=staff_id, created_at=datetime.now(),
            )
        )
        return int(conn.execute(select(db.menu.c.stock).where(db.menu.c.menu_id == menu_id)).scalar_one())


def low_stock(engine: Engine, threshold: int = LOW_STOCK_THRESHOLD) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT menu_id, menu_name, category, stock FROM menu WHERE is_active = 1 AND stock <= :t ORDER BY stock, menu_name"),
            conn,
            params={"t": threshold},
        )


def seed_menu_from_csv(engine: Engine, csv_path) -> int:
    """Masukkan menu dari CSV bila tabel masih kosong. Mengembalikan jumlah baris yang dimasukkan."""
    with engine.begin() as conn:
        if conn.execute(select(db.menu.c.menu_id).limit(1)).first():
            return 0
        df = pd.read_csv(csv_path)
        rows = [
            dict(menu_name=r.menu_name, category=r.category, price=int(r.price), stock=int(r.stock))
            for r in df.itertuples(index=False)
        ]
        conn.execute(insert(db.menu), rows)
        ids = conn.execute(select(db.menu.c.menu_id, db.menu.c.stock)).all()
        conn.execute(
            insert(db.stock_movements),
            [dict(menu_id=i, delta=s, reason="initial", created_at=datetime.now()) for i, s in ids if s > 0],
        )
        return len(rows)
