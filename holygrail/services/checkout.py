"""Checkout atomik: validasi, harga server-side, pengurangan stok, simpan transaksi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from .. import db
from ..errors import NotFoundError, PaymentError, StockError, ValidationError
from ..validation import MAX_QTY, parse_payment, parse_qty
from .customers import get_or_create_customer


@dataclass(frozen=True)
class ReceiptLine:
    menu_name: str
    qty: int
    unit_price: int
    subtotal: int


@dataclass(frozen=True)
class Receipt:
    trx_id: int
    customer_name: str
    created_at: datetime
    payment_method: str
    lines: tuple[ReceiptLine, ...]
    total: int
    paid: int
    change: int


def time_of_day(hour: int) -> str:
    if 5 <= hour < 11:
        return "Pagi"
    if 11 <= hour < 15:
        return "Siang"
    if 15 <= hour < 18:
        return "Sore"
    return "Malam"


def _merge_lines(lines: list[tuple[int, int]]) -> dict[int, int]:
    if not lines:
        raise ValidationError("Keranjang masih kosong.")
    merged: dict[int, int] = {}
    for menu_id, qty in lines:
        merged[int(menu_id)] = merged.get(int(menu_id), 0) + parse_qty(qty)
    if any(q > MAX_QTY for q in merged.values()):
        raise ValidationError(f"Jumlah per menu maksimal {MAX_QTY}.")
    return merged


def get_receipt(conn: Connection, trx_id: int) -> Receipt:
    t = conn.execute(
        select(db.transactions, db.customers.c.name.label("customer_name"))
        .join(db.customers, db.customers.c.customer_id == db.transactions.c.customer_id)
        .where(db.transactions.c.trx_id == trx_id)
    ).mappings().first()
    if not t:
        raise NotFoundError("Transaksi tidak ditemukan.")
    items = conn.execute(
        select(db.menu.c.menu_name, db.transaction_items.c.qty, db.transaction_items.c.unit_price, db.transaction_items.c.subtotal)
        .join(db.menu, db.menu.c.menu_id == db.transaction_items.c.menu_id)
        .where(db.transaction_items.c.trx_id == trx_id)
        .order_by(db.transaction_items.c.item_id)
    ).all()
    return Receipt(
        trx_id=t["trx_id"], customer_name=t["customer_name"], created_at=t["created_at"],
        payment_method=t["payment_method"], lines=tuple(ReceiptLine(*i) for i in items),
        total=t["total"], paid=t["paid"], change=t["change_amount"],
    )


def checkout(
    engine: Engine,
    *,
    lines: list[tuple[int, int]],
    customer_name: str,
    payment_method: str,
    paid: object,
    weather: str,
    group_size: str,
    cashier_id: int | None,
    idempotency_key: str,
    now: datetime | None = None,
) -> Receipt:
    """Proses satu pembayaran. Semua-atau-tidak-sama-sekali; aman dipanggil ulang dengan kunci yang sama."""
    if payment_method not in db.PAYMENT_METHODS:
        raise ValidationError("Metode pembayaran tidak dikenal.")
    if weather not in db.WEATHERS or group_size not in db.GROUP_SIZES:
        raise ValidationError("Konteks pesanan tidak valid.")
    if not idempotency_key or len(idempotency_key) > 64:
        raise ValidationError("Kunci transaksi tidak valid.")
    merged = _merge_lines(lines)
    paid_in = parse_payment(paid)
    now = now or datetime.now()

    try:
        with engine.begin() as conn:
            existing = conn.execute(
                select(db.transactions.c.trx_id).where(db.transactions.c.idempotency_key == idempotency_key)
            ).scalar()
            if existing is not None:
                return get_receipt(conn, int(existing))

            customer_id = get_or_create_customer(conn, customer_name)

            rows = conn.execute(
                select(db.menu.c.menu_id, db.menu.c.menu_name, db.menu.c.price, db.menu.c.stock, db.menu.c.is_active)
                .where(db.menu.c.menu_id.in_(list(merged)))
            ).all()
            by_id = {r.menu_id: r for r in rows}
            total = 0
            for menu_id, qty in merged.items():
                row = by_id.get(menu_id)
                if row is None or not row.is_active:
                    raise ValidationError("Ada menu di keranjang yang sudah tidak tersedia. Muat ulang halaman.")
                total += row.price * qty

            if payment_method == "Tunai":
                if paid_in < total:
                    raise PaymentError(f"Uang kurang Rp {total - paid_in:,}.".replace(",", "."))
                paid_final = paid_in
            else:
                paid_final = total  # non-tunai dibayar pas

            trx_id = int(
                conn.execute(
                    insert(db.transactions).values(
                        idempotency_key=idempotency_key, customer_id=customer_id, cashier_id=cashier_id,
                        created_at=now, weather=weather, group_size=group_size, time_of_day=time_of_day(now.hour),
                        payment_method=payment_method, total=total, paid=paid_final, change_amount=paid_final - total,
                    )
                ).inserted_primary_key[0]
            )

            for menu_id, qty in merged.items():
                row = by_id[menu_id]
                # Pengurangan stok atomik: gagal bila stok tidak cukup (mencegah oversell).
                res = conn.execute(
                    update(db.menu).where(db.menu.c.menu_id == menu_id, db.menu.c.stock >= qty)
                    .values(stock=db.menu.c.stock - qty)
                )
                if res.rowcount == 0:
                    left = conn.execute(select(db.menu.c.stock).where(db.menu.c.menu_id == menu_id)).scalar_one()
                    raise StockError(f"Stok '{row.menu_name}' tidak cukup (tersisa {left}).")
                conn.execute(
                    insert(db.transaction_items).values(
                        trx_id=trx_id, menu_id=menu_id, qty=qty, unit_price=row.price, subtotal=row.price * qty
                    )
                )
                conn.execute(
                    insert(db.stock_movements).values(
                        menu_id=menu_id, delta=-qty, reason="sale", trx_id=trx_id, staff_id=cashier_id, created_at=now
                    )
                )
            return get_receipt(conn, trx_id)
    except IntegrityError:
        # Dua klik bersamaan dengan kunci sama: ambil transaksi yang sudah tersimpan.
        with engine.connect() as conn:
            existing = conn.execute(
                select(db.transactions.c.trx_id).where(db.transactions.c.idempotency_key == idempotency_key)
            ).scalar()
            if existing is not None:
                return get_receipt(conn, int(existing))
        raise ValidationError("Transaksi gagal disimpan. Periksa data lalu coba lagi.") from None
