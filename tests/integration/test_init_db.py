import sqlite3

from scripts import init_db


def test_init_db_creates_schema_menu_and_staff_idempotently(tmp_path, monkeypatch, capsys):
    path = tmp_path / "hg.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin-Init-2026x")
    monkeypatch.delenv("KASIR_PASSWORD", raising=False)  # akan dibuat acak & dicetak
    assert init_db.main([]) == 0
    out = capsys.readouterr().out
    assert "70 item baru" in out and "Akun dibuat: kasir" in out

    con = sqlite3.connect(path)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"staff", "customers", "menu", "transactions", "transaction_items", "stock_movements"} <= tables
    assert con.execute("select count(*) from menu").fetchone()[0] == 70
    assert con.execute("select count(*) from staff").fetchone()[0] == 2
    assert con.execute("pragma integrity_check").fetchone()[0] == "ok"
    con.close()

    assert init_db.main([]) == 0  # kedua kalinya: tidak menggandakan apa pun
    assert "0 item baru" in capsys.readouterr().out
    con = sqlite3.connect(path)
    assert con.execute("select count(*) from menu").fetchone()[0] == 70
    assert con.execute("select count(*) from staff").fetchone()[0] == 2


def test_init_db_rejects_weak_admin_password(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    assert init_db.main([]) == 1
