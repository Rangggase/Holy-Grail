"""Uji end-to-end: menjalankan app.py sungguhan lewat Streamlit AppTest (tanpa browser), dengan database sementara."""

from pathlib import Path

import pytest
from sqlalchemy import select, text
from streamlit.testing.v1 import AppTest

from holygrail import db
from holygrail.config import SEED_MENU_CSV
from holygrail.services import auth, menu as menu_svc
from scripts.seed_demo import seed_demo

APP = str(Path(__file__).resolve().parents[2] / "app.py")
ADMIN_PW, KASIR_PW = "Admin-Test-2026x", "Kasir-Test-2026x"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'e2e.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MAX_LOGIN_ATTEMPTS", "3")
    engine = db.make_engine(url)
    db.create_schema(engine)
    menu_svc.seed_menu_from_csv(engine, SEED_MENU_CSV)
    auth.create_staff(engine, username="admin", full_name="Admin Uji", password=ADMIN_PW, role="admin")
    auth.create_staff(engine, username="kasir", full_name="Kasir Uji", password=KASIR_PW, role="kasir")
    seed_demo(engine, n_customers=40, n_transactions=300, seed=7)
    return engine


def new_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=90).run()


def login(at: AppTest, user: str, pw: str) -> AppTest:
    at.text_input[0].set_value(user)
    at.text_input[1].set_value(pw)
    at.button[0].click()
    return at.run()


def menu_id(engine, name):
    with engine.connect() as c:
        return c.execute(select(db.menu.c.menu_id).where(db.menu.c.menu_name == name)).scalar_one()


def test_login_page_renders_without_errors(env):
    at = new_app()
    assert not at.exception
    assert [t.label for t in at.text_input] == ["Username", "Password"]


def test_wrong_password_shows_generic_error_and_locks_after_max_attempts(env):
    at = new_app()
    for _ in range(3):
        at = login(at, "admin", "salah-banget")
        assert any("Username atau password salah" in e.value for e in at.error)
    assert "staff" not in at.session_state
    at = login(at, "admin", ADMIN_PW)  # benar, tetapi terkunci
    assert any("Terlalu banyak percobaan" in e.value for e in at.error)
    assert "staff" not in at.session_state


def test_kasir_full_sale_flow(env):
    at = login(new_app(), "kasir", KASIR_PW)
    assert not at.exception and at.session_state["staff"].role == "kasir"
    nasi = menu_id(env, "Nasi Goreng Spesial")
    with env.connect() as c:
        before = c.execute(text("select stock from menu where menu_id=:i"), {"i": nasi}).scalar()

    at.text_input(key="cust_name").set_value("Pelanggan Uji Coba").run()
    at.button(key=f"add_{nasi}").click().run()
    at.button(key=f"inc_{nasi}").click().run()
    assert at.session_state["cart"] == {nasi: 2}

    at.number_input(key="cash").set_value(40_000).run()  # total 50.000 -> kurang
    assert at.button(key="btn_pay").disabled
    assert any("Uang kurang" in w.value for w in at.warning)

    at.number_input(key="cash").set_value(100_000).run()
    assert not at.button(key="btn_pay").disabled
    at.button(key="btn_pay").click().run()
    assert not at.exception
    r = at.session_state["receipt"]
    assert r is not None and r.total == 50_000 and r.change == 50_000 and r.customer_name == "Pelanggan Uji Coba"
    assert at.session_state["cart"] == {}
    with env.connect() as c:
        after = c.execute(text("select stock from menu where menu_id=:i"), {"i": nasi}).scalar()
        assert c.execute(text("select count(*) from transactions where trx_id=:t"), {"t": r.trx_id}).scalar() == 1
    assert after == before - 2

    at.button(key="btn_new_sale").click().run()
    assert at.session_state["receipt"] is None


def test_cannot_exceed_stock(env):
    with env.begin() as c:
        c.execute(text("update menu set stock=1 where menu_name='Es Jeruk Murni'"))
    at = login(new_app(), "kasir", KASIR_PW)
    mid = menu_id(env, "Es Jeruk Murni")
    at.button(key=f"add_{mid}").click().run()
    assert at.session_state["cart"] == {mid: 1}
    assert at.button(key=f"add_{mid}").disabled


def test_kasir_cannot_open_admin_page(env):
    at = login(new_app(), "kasir", KASIR_PW)
    assert [b.key for b in at.button if b.key == "nav_admin"] == []
    at.session_state["page"] = "admin"  # coba paksa lewat state
    at.run()
    assert not any(t.value == "Dasbor admin" for t in at.title)


def test_admin_dashboard_and_stock_adjustment(env):
    at = login(new_app(), "admin", ADMIN_PW)
    at.button(key="nav_admin").click().run()
    assert not at.exception
    assert any(t.value == "Dasbor admin" for t in at.title)
    assert [t.label for t in at.tabs] == ["Ringkasan", "Pelanggan", "Menu & stok", "Transaksi"]
    # Menyesuaikan stok lewat form admin
    mid = menu_id(env, "Soto Betawi")
    with env.connect() as c:
        before = c.execute(text("select stock from menu where menu_id=:i"), {"i": mid}).scalar()
    at.selectbox(key="stock_menu").select("Soto Betawi — Makanan Berat")
    at.number_input(key="stock_delta").set_value(5)
    next(b for b in at.button if b.label == "Simpan stok").click()
    at.run()
    assert not at.exception
    with env.connect() as c:
        assert c.execute(text("select stock from menu where menu_id=:i"), {"i": mid}).scalar() == before + 5


def test_logout_clears_session(env):
    at = login(new_app(), "kasir", KASIR_PW)
    at.button(key="nav_logout").click().run()
    assert "staff" not in at.session_state
    assert [t.label for t in at.text_input] == ["Username", "Password"]
