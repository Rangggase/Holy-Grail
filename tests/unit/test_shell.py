from datetime import date

import pytest

from holygrail.ui.components import badge, date_id, esc, rupiah
from holygrail.ui.shell import NAV, allowed, resolve_page


def test_kasir_only_sees_pos_terminal():
    assert [n.page for n in NAV if allowed(n.page, "kasir")] == ["kasir"]
    assert [n.page for n in NAV if allowed(n.page, "admin")] == ["kasir", "dashboard", "menu", "riwayat"]


@pytest.mark.parametrize("requested,role,expected", [
    ("dashboard", "admin", "dashboard"), ("menu", "admin", "menu"), ("riwayat", "admin", "riwayat"),
    ("dashboard", "kasir", "kasir"), ("menu", "kasir", "kasir"), ("riwayat", "kasir", "kasir"),
    (None, "admin", "kasir"), ("tidak-ada", "admin", "kasir"), ("", "kasir", "kasir"),
])
def test_resolve_page_enforces_role(requested, role, expected):
    assert resolve_page(requested, role) == expected


def test_navigation_groups_match_spec():
    groups = {n.group for n in NAV}
    assert groups == {"Operasional", "Administrasi"}
    assert {n.label for n in NAV} == {"POS Terminal", "Dasbor Analitik", "Menu & Stok", "Riwayat Transaksi"}


def test_indonesian_date_and_money_formatting():
    assert date_id(date(2026, 11, 16)) == "Senin, 16 November 2026"
    assert date_id(date(2026, 8, 17)) == "Senin, 17 Agustus 2026"
    assert rupiah(1234567) == "Rp 1.234.567" and rupiah(0) == "Rp 0"


def test_html_helpers_escape_untrusted_text():
    assert "<script>" not in esc("<script>alert(1)</script>")
    assert "<img" not in badge("<img src=x onerror=1>")
