"""Validasi & sanitasi input pengguna. Semua pesan berbahasa Indonesia."""

from __future__ import annotations

import re
import unicodedata

from .errors import ValidationError

MAX_QTY = 99
MAX_PRICE = 100_000_000
MAX_PAYMENT = 1_000_000_000

_NAME_RE = re.compile(r"^[\w .,'\-]+$", re.UNICODE)
_USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,40}$")


def _strip_controls(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")


def clean_text(raw: object, *, field: str, min_len: int, max_len: int) -> str:
    if raw is None:
        raise ValidationError(f"{field} wajib diisi.")
    text = " ".join(_strip_controls(str(raw)).split())
    if len(text) < min_len:
        raise ValidationError(f"{field} minimal {min_len} karakter.")
    if len(text) > max_len:
        raise ValidationError(f"{field} maksimal {max_len} karakter.")
    return text


def clean_person_name(raw: object, *, field: str = "Nama pelanggan") -> str:
    text = clean_text(raw, field=field, min_len=2, max_len=60)
    if not _NAME_RE.match(text):
        raise ValidationError(f"{field} hanya boleh berisi huruf, angka, spasi, titik, koma, apostrof, dan tanda hubung.")
    return text


def clean_menu_name(raw: object) -> str:
    text = clean_text(raw, field="Nama menu", min_len=2, max_len=80)
    if not re.match(r"^[\w .,'\-()&/]+$", text, re.UNICODE):
        raise ValidationError("Nama menu mengandung karakter yang tidak diperbolehkan.")
    return text


def clean_category(raw: object) -> str:
    return clean_text(raw, field="Kategori", min_len=2, max_len=40)


def clean_username(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if not _USERNAME_RE.match(text):
        raise ValidationError("Username 3–40 karakter: huruf kecil, angka, titik, atau garis bawah.")
    return text


def parse_int(raw: object, *, field: str, minimum: int, maximum: int) -> int:
    if isinstance(raw, bool):
        raise ValidationError(f"{field} tidak valid.")
    try:
        if isinstance(raw, float):
            if raw != int(raw):
                raise ValueError
            value = int(raw)
        else:
            value = int(str(raw).strip().replace(".", "").replace(",", ""))
    except (ValueError, TypeError):
        raise ValidationError(f"{field} harus berupa angka bulat.") from None
    if value < minimum:
        raise ValidationError(f"{field} minimal {minimum:,}.".replace(",", "."))
    if value > maximum:
        raise ValidationError(f"{field} maksimal {maximum:,}.".replace(",", "."))
    return value


def parse_qty(raw: object) -> int:
    return parse_int(raw, field="Jumlah", minimum=1, maximum=MAX_QTY)


def parse_price(raw: object) -> int:
    return parse_int(raw, field="Harga", minimum=1, maximum=MAX_PRICE)


def parse_payment(raw: object) -> int:
    return parse_int(raw, field="Uang diterima", minimum=0, maximum=MAX_PAYMENT)
