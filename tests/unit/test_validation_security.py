import pytest

from holygrail import security, validation as v
from holygrail.errors import ValidationError


def test_password_hash_roundtrip_and_unique_salt():
    h1, h2 = security.hash_password("Rahasia-2026"), security.hash_password("Rahasia-2026")
    assert h1 != h2 and h1.startswith("scrypt$")
    assert security.verify_password("Rahasia-2026", h1)
    assert not security.verify_password("salah", h1)
    assert not security.verify_password("x", "bukan-hash")


@pytest.mark.parametrize("pw", ["pendek1", "adminadmin", "12345678", "admin123", "ganti-password-ini"])
def test_weak_passwords_rejected(pw):
    with pytest.raises(ValidationError):
        security.validate_password_strength(pw)


def test_strong_password_ok():
    security.validate_password_strength("Rahasia-2026")


def test_throttle_locks_after_max_attempts_and_unlocks():
    t = security.LoginThrottle(max_attempts=3, lockout_seconds=60)
    for _ in range(3):
        assert not t.is_locked(100)
        t.record_failure(100)
    assert t.is_locked(101) and t.remaining_lock(101) == 59
    assert not t.is_locked(161)
    t.record_success()
    assert t.failures == 0


@pytest.mark.parametrize("raw,expected", [("  Budi   Santoso ", "Budi Santoso"), ("Siti-Nur. A'ini", "Siti-Nur. A'ini")])
def test_clean_person_name_ok(raw, expected):
    assert v.clean_person_name(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "A", "x" * 61, "<script>alert(1)</script>", "Budi; DROP TABLE", None])
def test_clean_person_name_rejects(raw):
    with pytest.raises(ValidationError):
        v.clean_person_name(raw)


def test_control_chars_stripped():
    assert v.clean_person_name("Bu\x00di\n Test") == "Budi Test"


@pytest.mark.parametrize("raw,expected", [("5", 5), (3, 3), ("1.500", 1500), (2.0, 2)])
def test_parse_int_ok(raw, expected):
    assert v.parse_int(raw, field="X", minimum=0, maximum=10_000) == expected


@pytest.mark.parametrize("raw", ["abc", "", None, True, 2.5, "-1", "10000000000"])
def test_parse_int_rejects(raw):
    with pytest.raises(ValidationError):
        v.parse_int(raw, field="X", minimum=0, maximum=1_000_000)


def test_qty_bounds():
    assert v.parse_qty(99) == 99
    for bad in (0, 100, -1):
        with pytest.raises(ValidationError):
            v.parse_qty(bad)


def test_username_rules():
    assert v.clean_username(" Admin ") == "admin"
    with pytest.raises(ValidationError):
        v.clean_username("a b")
