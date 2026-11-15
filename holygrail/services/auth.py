"""Autentikasi & manajemen akun staf."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .. import db
from ..errors import AuthError, ValidationError
from ..security import DUMMY_HASH, hash_password, validate_password_strength, verify_password
from ..validation import clean_person_name, clean_username


@dataclass(frozen=True)
class Staff:
    staff_id: int
    username: str
    full_name: str
    role: str


def create_staff(engine: Engine, *, username: str, full_name: str, password: str, role: str) -> int:
    if role not in db.ROLES:
        raise ValidationError("Peran tidak dikenal.")
    username = clean_username(username)
    full_name = clean_person_name(full_name, field="Nama lengkap")
    validate_password_strength(password)
    try:
        with engine.begin() as conn:
            res = conn.execute(
                insert(db.staff).values(
                    username=username, full_name=full_name, password_hash=hash_password(password), role=role
                )
            )
            return int(res.inserted_primary_key[0])
    except IntegrityError:
        raise ValidationError(f"Username '{username}' sudah dipakai.") from None


def authenticate(engine: Engine, username: str, password: str) -> Staff:
    """Kembalikan Staff bila valid; selain itu AuthError dengan pesan generik (tidak membocorkan alasan)."""
    generic = AuthError("Username atau password salah.")
    uname = str(username or "").strip().lower()
    with engine.connect() as conn:
        row = conn.execute(select(db.staff).where(db.staff.c.username == uname)).mappings().first()
    stored = row["password_hash"] if row else DUMMY_HASH
    ok = verify_password(password or "", stored)
    if not row or not ok or not row["is_active"]:
        raise generic
    return Staff(row["staff_id"], row["username"], row["full_name"], row["role"])
