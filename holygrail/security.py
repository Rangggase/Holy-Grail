"""Keamanan: hash password (scrypt, stdlib) dan pembatas percobaan login."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass, field

from .errors import ValidationError

_N, _R, _P = 2**14, 8, 1
_WEAK = {"password", "12345678", "admin123", "admin1234", "qwerty123", "password1", "ganti-password-ini"}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(hash_b64)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# Hash tiruan untuk menyamakan waktu respons saat username tidak ada.
DUMMY_HASH = hash_password(secrets.token_urlsafe(8))


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValidationError("Password minimal 8 karakter.")
    if password.lower() in _WEAK:
        raise ValidationError("Password terlalu umum. Gunakan kombinasi yang lebih sulit ditebak.")
    if password.isalpha() or password.isdigit():
        raise ValidationError("Password harus mengandung kombinasi huruf dan angka.")


@dataclass
class LoginThrottle:
    """Batasi percobaan login beruntun. Disimpan per sesi pengguna (lihat catatan keamanan di README)."""

    max_attempts: int = 5
    lockout_seconds: int = 60
    failures: int = 0
    locked_until: float = 0.0
    _clock_skew: float = field(default=0.0, repr=False)

    def remaining_lock(self, now: float) -> int:
        return max(0, int(self.locked_until - now + 0.999))

    def is_locked(self, now: float) -> bool:
        return now < self.locked_until

    def record_failure(self, now: float) -> None:
        self.failures += 1
        if self.failures >= self.max_attempts:
            self.locked_until = now + self.lockout_seconds
            self.failures = 0

    def record_success(self) -> None:
        self.failures = 0
        self.locked_until = 0.0
