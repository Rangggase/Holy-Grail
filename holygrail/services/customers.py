"""Pelanggan (member)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection, Engine

from .. import db
from ..validation import clean_person_name


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_customers(engine: Engine, term: str, limit: int = 5) -> list[Customer]:
    term = " ".join(str(term or "").split()).lower()
    if len(term) < 2:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            select(db.customers.c.customer_id, db.customers.c.name)
            .where(db.customers.c.name_key.like(f"%{_escape_like(term)}%", escape="\\"))
            .order_by(func.length(db.customers.c.name_key), db.customers.c.name_key)
            .limit(limit)
        ).all()
    return [Customer(r[0], r[1]) for r in rows]


def get_or_create_customer(conn: Connection, name: str) -> int:
    """Cari pelanggan berdasarkan nama (tidak peka huruf besar/kecil); buat bila belum ada."""
    name = clean_person_name(name)
    key = name.lower()
    found = conn.execute(select(db.customers.c.customer_id).where(db.customers.c.name_key == key)).scalar()
    if found is not None:
        return int(found)
    return int(conn.execute(insert(db.customers).values(name=name, name_key=key)).inserted_primary_key[0])
