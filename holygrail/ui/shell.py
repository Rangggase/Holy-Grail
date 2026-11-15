"""App shell: sidebar terstruktur + bilah konteks atas + guard halaman per peran."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import streamlit as st
from sqlalchemy import text

from ..config import Settings
from ..services import menu as menu_svc
from ..services import reports
from ..services.checkout import time_of_day
from .components import brand_block, date_id, esc, number_id, rupiah, top_bar


@dataclass(frozen=True)
class NavItem:
    page: str
    label: str
    icon: str
    group: str
    admin_only: bool = False


NAV = (
    NavItem("kasir", "POS Terminal", "point_of_sale", "Operasional"),
    NavItem("dashboard", "Dasbor Analitik", "monitoring", "Administrasi", True),
    NavItem("menu", "Menu & Stok", "inventory_2", "Administrasi", True),
    NavItem("riwayat", "Riwayat Transaksi", "receipt_long", "Administrasi", True),
)
PAGES = {n.page: n for n in NAV}


def allowed(page: str, role: str) -> bool:
    item = PAGES.get(page)
    return item is not None and (role == "admin" or not item.admin_only)


def resolve_page(requested: str | None, role: str) -> str:
    """Halaman yang diminta bila diizinkan untuk peran ini; selain itu kembali ke kasir."""
    return requested if requested and allowed(requested, role) else "kasir"


def _go(page: str) -> None:
    st.session_state["page"] = page
    try:
        st.query_params["hal"] = page  # tautan dalam-sesi: halaman tercermin di URL
    except Exception:  # noqa: BLE001 - tidak kritis
        pass


def _logout() -> None:
    for key in ("staff", "cart", "receipt", "idem", "cash", "page"):
        st.session_state.pop(key, None)
    try:
        st.query_params.clear()
    except Exception:  # noqa: BLE001
        pass


def db_status(engine) -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, {"sqlite": "SQLite", "postgresql": "PostgreSQL"}.get(engine.dialect.name, engine.dialect.name)
    except Exception:  # noqa: BLE001
        return False, "Tidak terhubung"


def render_sidebar(engine, staff, settings: Settings, page: str) -> None:
    with st.sidebar:
        st.markdown(brand_block(settings.store_name), unsafe_allow_html=True)
        last_group = ""
        for item in NAV:
            if not allowed(item.page, staff.role):
                continue
            if item.group != last_group:
                st.markdown(f'<p class="side-group">{esc(item.group)}</p>', unsafe_allow_html=True)
                last_group = item.group
            active = item.page == page
            with st.container(key=f"nav_item_{'on_' if active else ''}{item.page}"):
                st.button(item.label, icon=f":material/{item.icon}:", key=f"nav_{item.page}", on_click=_go, args=(item.page,),
                          use_container_width=True, type="secondary")
        with st.container(key="side_footer"):
            initials = "".join(w[0] for w in staff.full_name.split()[:2]).upper() or "?"
            role = "Administrator" if staff.role == "admin" else "Kasir"
            ok, label = db_status(engine)
            st.markdown(
                f'<div class="profile"><div class="avatar" aria-hidden="true">{esc(initials)}</div>'
                f'<div><b>{esc(staff.full_name)}</b><span class="role">{role}</span></div></div>'
                f'<div class="dbstat"><span class="dot{"" if ok else " off"}" aria-hidden="true"></span>'
                f'<span>Database: {"terhubung" if ok else "terputus"} ({esc(label)})</span></div>',
                unsafe_allow_html=True,
            )
            st.button("Keluar", icon=":material/logout:", key="nav_logout", on_click=_logout, use_container_width=True)


_TITLES = {
    "kasir": ("POS Terminal", "Catat pesanan dan terima pembayaran"),
    "dashboard": ("Dasbor Analitik", "Ringkasan penjualan, tren, dan pelanggan"),
    "menu": ("Menu & Stok", "Kelola daftar menu, harga, dan persediaan"),
    "riwayat": ("Riwayat Transaksi", "Telusuri dan ekspor transaksi"),
}


def render_top_bar(engine, staff, page: str, now: datetime | None = None) -> None:
    now = now or datetime.now()
    title, sub = _TITLES[page]
    today = reports.today_summary(engine, now.date())
    chips: list[tuple[str, str, bool]] = [
        ("calendar_today", f"<b>{esc(date_id(now.date()))}</b>", False),
        ("schedule", f"Shift <b>{esc(time_of_day(now.hour).lower())}</b> · {now:%H:%M}", False),
        ("payments", f"Hari ini <b>{esc(rupiah(today.revenue))}</b> · {number_id(today.transactions)} transaksi", False),
    ]
    if page == "kasir":
        items = sum(st.session_state.get("cart", {}).values())
        chips.append(("shopping_cart", f"Keranjang <b>{items}</b> item", False))
    low = len(menu_svc.low_stock(engine))
    if low:
        chips.append(("inventory", f"Stok menipis <b>{low}</b>", True))
    top_bar(title, f"{sub} · {staff.full_name}", chips)
