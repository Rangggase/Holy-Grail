"""Komponen UI bersama. Semua data dinamis yang masuk HTML wajib lewat `esc()`."""

from __future__ import annotations

import html
import logging
from datetime import date

import streamlit as st

from ..errors import HolyGrailError
from .theme import BRAND_SVG

log = logging.getLogger("holygrail")

_HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
_BULAN = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def rupiah(amount: int | float) -> str:
    """12500 -> 'Rp 12.500' (titik sebagai pemisah ribuan)."""
    return "Rp " + f"{int(round(amount)):,}".replace(",", ".")


def number_id(value: int | float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def date_id(d: date) -> str:
    """date(2026,11,16) -> 'Senin, 16 November 2026' (tanpa bergantung pada locale OS)."""
    return f"{_HARI[d.weekday()]}, {d.day} {_BULAN[d.month - 1]} {d.year}"


def icon(name: str) -> str:
    """Ikon Material Symbols (set yang sama dengan ikon tombol Streamlit); dekoratif, disembunyikan dari pembaca layar."""
    return f'<span class="ms" aria-hidden="true">{esc(name)}</span>'


def badge(text: str, tone: str = "") -> str:
    return f'<span class="badge {esc(tone)}">{esc(text)}</span>'


def show_error(exc: Exception) -> None:
    """Pesan ramah untuk pengguna; detail teknis hanya ke log."""
    if isinstance(exc, HolyGrailError):
        st.error(str(exc), icon=":material/error:")
    else:
        log.exception("Kesalahan tak terduga", exc_info=exc)
        st.error("Terjadi gangguan pada sistem. Coba lagi sebentar; bila berulang, hubungi admin.", icon=":material/error:")


def kpi(label: str, value: str, hint: str = "", *, icon_name: str = "", small: bool = False) -> None:
    st.markdown(
        f'<div class="kpi"><div class="top"><span>{esc(label)}</span>{icon(icon_name) if icon_name else ""}</div>'
        f'<div class="v{" sm" if small else ""}">{esc(value)}</div><div class="h">{esc(hint)}</div></div>',
        unsafe_allow_html=True,
    )


def card_title(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="card-title">{esc(title)}</div>' + (f'<div class="card-sub">{esc(sub)}</div>' if sub else ""), unsafe_allow_html=True)


def brand_block(subtitle: str) -> str:
    return f'<div class="side-brand">{BRAND_SVG}<div><b>Holy Grail</b><span>{esc(subtitle)}</span></div></div>'


def top_bar(title: str, subtitle: str, chips: list[tuple[str, str, bool]]) -> None:
    """Bilah konteks: judul halaman + subjudul di kiri; chip status (ikon, teks, peringatan?) di kanan."""
    chip_html = "".join(
        f'<span class="chip{" warn" if warn else ""}">{icon(ic)}<span>{text}</span></span>' for ic, text, warn in chips
    )
    st.markdown(
        f'<div class="topbar"><div><h1>{esc(title)}</h1><div class="sub">{esc(subtitle)}</div></div><div class="chips">{chip_html}</div></div>',
        unsafe_allow_html=True,
    )
