"""Konfigurasi aplikasi. Satu-satunya modul yang membaca environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = ROOT_DIR / "data" / "holygrail.db"
SEED_MENU_CSV = ROOT_DIR / "data" / "seed" / "menu.csv"


@dataclass(frozen=True)
class Settings:
    database_url: str
    store_name: str
    max_login_attempts: int
    lockout_seconds: int


def default_database_url() -> str:
    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def get_settings() -> Settings:
    """Baca setting dari environment (dan .env bila ada). Dipanggil ulang tiap kali agar mudah diuji."""
    load_dotenv(ROOT_DIR / ".env", override=False)
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "").strip() or default_database_url(),
        store_name=os.environ.get("STORE_NAME", "Holy Grail Resto").strip() or "Holy Grail Resto",
        max_login_attempts=int(os.environ.get("MAX_LOGIN_ATTEMPTS", "5")),
        lockout_seconds=int(os.environ.get("LOCKOUT_SECONDS", "60")),
    )
