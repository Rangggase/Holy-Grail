import threading
from datetime import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from holygrail import db
from holygrail.errors import PaymentError, StockError, ValidationError
from holygrail.services import auth, menu as menu_svc
from holygrail.services.checkout import checkout, time_of_day
from tests.conftest import menu_id

CTX = dict(weather="Cerah", group_size="Sendiri")


def pay(engine, lines, *, key="k1", name="Budi Santoso", method="Tunai", paid=1_000_000, **kw):
    return checkout(engine, lines=lines, customer_name=name, payment_method=method, paid=paid,
                    cashier_id=kw.pop("cashier_id", None), idempotency_key=key, **CTX, **kw)


def stock(engine, name):
    with engine.connect() as c:
        return c.execute(select(db.menu.c.stock).where(db.menu.c.menu_name == name)).scalar_one()


def count(engine, table):
    with engine.connect() as c:
        return c.execute(text(f"select count(*) from {table}")).scalar()


def test_checkout_computes_total_change_and_reduces_stock(engine, kasir_id):
    nasi, teh = menu_id(engine, "Nasi Goreng Spesial"), menu_id(engine, "Es Teh Manis")
    r = pay(engine, [(nasi, 2), (teh, 1), (nasi, 1)], paid=100_000, cashier_id=kasir_id, now=datetime(2026, 1, 5, 12, 0))
    assert r.total == 3 * 25000 + 7000 == 82_000
    assert r.change == 18_000 and len(r.lines) == 2
    assert stock(engine, "Nasi Goreng Spesial") == 7 and stock(engine, "Es Teh Manis") == 4
    with engine.connect() as c:
        tod = c.execute(text("select time_of_day from transactions")).scalar()
        mv = c.execute(text("select count(*) from stock_movements where reason='sale'")).scalar()
    assert tod == "Siang" and mv == 2


def test_price_is_read_server_side_and_snapshotted(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    pay(engine, [(nasi, 1)], key="a")
    menu_svc.update_menu(engine, nasi, name="Nasi Goreng Spesial", category="Makanan Berat", price=30000, is_active=True)
    with engine.connect() as c:
        assert c.execute(text("select unit_price from transaction_items")).scalar() == 25000


def test_insufficient_cash_rejected_and_nothing_saved(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    with pytest.raises(PaymentError, match="kurang"):
        pay(engine, [(nasi, 2)], paid=10_000)
    assert stock(engine, "Nasi Goreng Spesial") == 10
    assert count(engine, "transactions") == 0 and count(engine, "customers") == 0


def test_oversell_rolls_back_whole_cart(engine):
    nasi, soto = menu_id(engine, "Nasi Goreng Spesial"), menu_id(engine, "Soto Betawi")
    with pytest.raises(StockError, match="Soto Betawi"):
        pay(engine, [(nasi, 1), (soto, 3)])
    assert stock(engine, "Nasi Goreng Spesial") == 10 and stock(engine, "Soto Betawi") == 2
    assert count(engine, "transaction_items") == 0 and count(engine, "transactions") == 0


def test_non_cash_is_paid_exact(engine):
    r = pay(engine, [(menu_id(engine, "Es Teh Manis"), 2)], method="QRIS", paid=0)
    assert r.paid == r.total == 14000 and r.change == 0


def test_idempotency_key_prevents_double_charge(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    a, b = pay(engine, [(nasi, 1)], key="same"), pay(engine, [(nasi, 1)], key="same")
    assert a.trx_id == b.trx_id and stock(engine, "Nasi Goreng Spesial") == 9


def test_concurrent_checkouts_never_oversell(engine):
    paket = menu_id(engine, "Paket Hemat Ber-4")  # stok 3
    results = []

    def go(i):
        try:
            pay(engine, [(paket, 1)], key=f"c{i}", name=f"Pelanggan {i}")
            results.append("ok")
        except StockError:
            results.append("habis")

    ts = [threading.Thread(target=go, args=(i,)) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert results.count("ok") == 3 and stock(engine, "Paket Hemat Ber-4") == 0


def test_customer_matching_is_case_insensitive(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    pay(engine, [(nasi, 1)], key="1", name="Budi Santoso")
    pay(engine, [(nasi, 1)], key="2", name="  budi   santoso ")
    assert count(engine, "customers") == 1


@pytest.mark.parametrize("kwargs", [
    dict(lines=[]), dict(name="<b>x</b>"), dict(method="Kripto"), dict(paid="abc"), dict(key=""),
])
def test_invalid_input_rejected(engine, kwargs):
    lines = kwargs.pop("lines", [(menu_id(engine, "Es Teh Manis"), 1)])
    with pytest.raises(ValidationError):
        pay(engine, lines, **kwargs)


def test_unknown_or_inactive_menu_rejected(engine):
    with pytest.raises(ValidationError):
        pay(engine, [(9999, 1)])
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    menu_svc.update_menu(engine, nasi, name="Nasi Goreng Spesial", category="Makanan Berat", price=25000, is_active=False)
    with pytest.raises(ValidationError):
        pay(engine, [(nasi, 1)], key="z")


# ---- constraint di level database (bukan hanya aplikasi) ----
def _raw(engine, sql, **p):
    with engine.begin() as c:
        c.execute(text(sql), p)


def test_db_rejects_negative_stock_and_bad_price(engine):
    with pytest.raises(IntegrityError):
        _raw(engine, "update menu set stock=-1 where menu_id=1")
    with pytest.raises(IntegrityError):
        _raw(engine, "update menu set price=0 where menu_id=1")


def test_db_rejects_duplicate_menu_name(engine):
    with pytest.raises(IntegrityError):
        _raw(engine, "insert into menu(menu_name,category,price,stock) values('Soto Betawi','X',1,1)")


def test_db_foreign_keys_enforced(engine):
    with pytest.raises(IntegrityError):
        _raw(engine, "insert into transaction_items(trx_id,menu_id,qty,unit_price,subtotal) values(999,1,1,1,1)")


def test_db_rejects_inconsistent_totals(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    r = pay(engine, [(nasi, 1)])
    with pytest.raises(IntegrityError):
        _raw(engine, "update transaction_items set subtotal=1 where trx_id=:t", t=r.trx_id)
    with pytest.raises(IntegrityError):
        _raw(engine, "update transactions set paid=1 where trx_id=:t", t=r.trx_id)
    with pytest.raises(IntegrityError):
        _raw(engine, "insert into transaction_items(trx_id,menu_id,qty,unit_price,subtotal) values(:t,:m,1,25000,25000)", t=r.trx_id, m=nasi)


def test_cannot_delete_menu_or_customer_with_history(engine):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    pay(engine, [(nasi, 1)])
    with pytest.raises(IntegrityError):
        _raw(engine, "delete from menu where menu_id=:m", m=nasi)
    with pytest.raises(IntegrityError):
        _raw(engine, "delete from customers")


# ---- auth ----
def test_auth_flow(engine):
    auth.create_staff(engine, username="Budi.Admin", full_name="Budi Admin", password="Rahasia-2026", role="admin")
    s = auth.authenticate(engine, "budi.admin", "Rahasia-2026")
    assert s.role == "admin"
    for u, p in (("budi.admin", "salah"), ("tidak.ada", "Rahasia-2026"), ("", "")):
        with pytest.raises(Exception, match="Username atau password salah"):
            auth.authenticate(engine, u, p)
    with pytest.raises(ValidationError, match="sudah dipakai"):
        auth.create_staff(engine, username="budi.admin", full_name="Dobel", password="Rahasia-2026", role="kasir")
    with pytest.raises(ValidationError):
        auth.create_staff(engine, username="x1y2", full_name="Lemah", password="admin123", role="kasir")


def test_passwords_are_not_stored_in_plaintext(engine, kasir_id):
    with engine.connect() as c:
        h = c.execute(text("select password_hash from staff")).scalar()
    assert "Rahasia-2026" not in h and h.startswith("scrypt$")


def test_inactive_staff_cannot_login(engine, kasir_id):
    _raw(engine, "update staff set is_active=0")
    with pytest.raises(Exception, match="salah"):
        auth.authenticate(engine, "kasir1", "Rahasia-2026")


# ---- menu & stok ----
def test_stock_adjustment_and_guard(engine, kasir_id):
    nasi = menu_id(engine, "Nasi Goreng Spesial")
    assert menu_svc.adjust_stock(engine, nasi, 5, reason="restock", staff_id=kasir_id) == 15
    with pytest.raises(StockError):
        menu_svc.adjust_stock(engine, nasi, -16, reason="adjustment", staff_id=kasir_id)
    with pytest.raises(ValidationError):
        menu_svc.adjust_stock(engine, nasi, 0, reason="restock", staff_id=kasir_id)
    assert stock(engine, "Nasi Goreng Spesial") == 15
    assert set(menu_svc.low_stock(engine, 3).menu_name) == {"Soto Betawi", "Paket Hemat Ber-4"}


def test_add_menu_validation_and_duplicates(engine):
    mid = menu_svc.add_menu(engine, name="Mie Aceh", category="Makanan Berat", price="28.000", stock=4)
    assert stock(engine, "Mie Aceh") == 4 and mid
    with pytest.raises(ValidationError, match="sudah ada"):
        menu_svc.add_menu(engine, name="Mie Aceh", category="Makanan Berat", price=1000)
    for bad in (dict(price=0), dict(price="abc"), dict(name="")):
        args = dict(name="Menu Baru", category="Snack", price=5000) | bad
        with pytest.raises(ValidationError):
            menu_svc.add_menu(engine, **args)


def test_time_of_day_buckets():
    assert [time_of_day(h) for h in (4, 5, 10, 11, 14, 15, 17, 18, 23)] == [
        "Malam", "Pagi", "Pagi", "Siang", "Siang", "Sore", "Sore", "Malam", "Malam"]
