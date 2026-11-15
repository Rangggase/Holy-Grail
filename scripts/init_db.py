"""Inisialisasi database: skema + seed menu + akun staf (+ data demo opsional).

Pemakaian:  python -m scripts.init_db [--demo] [--reset]
Password akun diambil dari .env (ADMIN_PASSWORD / KASIR_PASSWORD). Bila kosong, dibuat acak dan dicetak SEKALI.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys

from sqlalchemy import func, select

from holygrail import db
from holygrail.config import SEED_MENU_CSV, get_settings
from holygrail.errors import HolyGrailError
from holygrail.services import auth, menu as menu_svc


def _password(env_key: str) -> tuple[str, bool]:
    value = os.environ.get(env_key, "").strip()
    if value:
        return value, False
    return secrets.token_urlsafe(9) + "7a", True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inisialisasi database Holy Grail POS")
    ap.add_argument("--demo", action="store_true", help="isi data transaksi demo (±6.000 transaksi fiktif)")
    ap.add_argument("--reset", action="store_true", help="HAPUS semua tabel lalu buat ulang")
    args = ap.parse_args(argv)

    settings = get_settings()
    engine = db.make_engine(settings.database_url)
    if args.reset:
        db.metadata.drop_all(engine)
    db.create_schema(engine)

    inserted = menu_svc.seed_menu_from_csv(engine, SEED_MENU_CSV)
    print(f"Menu: {inserted} item baru dimasukkan.")

    created: list[tuple[str, str]] = []
    with engine.connect() as conn:
        have = {r[0] for r in conn.execute(select(db.staff.c.username))}
    for user_env, pass_env, default_user, name, role in (
        ("ADMIN_USERNAME", "ADMIN_PASSWORD", "admin", "Administrator", "admin"),
        ("KASIR_USERNAME", "KASIR_PASSWORD", "kasir", "Kasir Utama", "kasir"),
    ):
        username = os.environ.get(user_env, default_user).strip().lower() or default_user
        if username in have:
            continue
        password, generated = _password(pass_env)
        try:
            auth.create_staff(engine, username=username, full_name=name, password=password, role=role)
        except HolyGrailError as exc:
            print(f"GAGAL membuat akun '{username}': {exc}", file=sys.stderr)
            return 1
        created.append((username, password if generated else "(dari .env)"))
    for username, pw in created:
        print(f"Akun dibuat: {username}  password: {pw}")
    if any(pw != "(dari .env)" for _, pw in created):
        print("Simpan password acak di atas ke .env — tidak akan ditampilkan lagi.")

    if args.demo:
        with engine.connect() as conn:
            existing = conn.execute(select(func.count()).select_from(db.transactions)).scalar_one()
        if existing:
            print(f"Data demo dilewati: sudah ada {existing} transaksi (gunakan --reset untuk mengulang).")
        else:
            from scripts.seed_demo import seed_demo

            stats = seed_demo(engine)
            print(f"Data demo: {stats['customers']} pelanggan, {stats['transactions']} transaksi.")

    print(f"Database siap: {engine.url.render_as_string(hide_password=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
