import pytest
from sqlalchemy import insert, select

from holygrail import db
from holygrail.services import auth


@pytest.fixture()
def engine(tmp_path):
    eng = db.make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    db.create_schema(eng)
    with eng.begin() as conn:
        conn.execute(
            insert(db.menu),
            [
                dict(menu_name="Nasi Goreng Spesial", category="Makanan Berat", price=25000, stock=10),
                dict(menu_name="Es Teh Manis", category="Minuman", price=7000, stock=5),
                dict(menu_name="Soto Betawi", category="Makanan Berat", price=45000, stock=2),
                dict(menu_name="Paket Hemat Ber-4", category="Paket Jumbo", price=100000, stock=3),
            ],
        )
    return eng


@pytest.fixture()
def kasir_id(engine):
    return auth.create_staff(engine, username="kasir1", full_name="Kasir Satu", password="Rahasia-2026", role="kasir")


def menu_id(engine, name):
    with engine.connect() as c:
        return c.execute(select(db.menu.c.menu_id).where(db.menu.c.menu_name == name)).scalar_one()
