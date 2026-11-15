"""Komponen UI bersama. Semua data dinamis yang masuk HTML wajib lewat `esc()`."""

from __future__ import annotations

import html
import logging

import streamlit as st

from ..errors import HolyGrailError
from .theme import BRAND_SVG

log = logging.getLogger("holygrail")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def rupiah(amount: int | float) -> str:
    """12500 -> 'Rp 12.500' (titik sebagai pemisah ribuan)."""
    return "Rp " + f"{int(round(amount)):,}".replace(",", ".")


def number_id(value: int | float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def show_error(exc: Exception) -> None:
    """Pesan ramah untuk pengguna; detail teknis hanya ke log."""
    if isinstance(exc, HolyGrailError):
        st.error(str(exc), icon=":material/error:")
    else:
        log.exception("Kesalahan tak terduga", exc_info=exc)
        st.error("Terjadi gangguan pada sistem. Coba lagi sebentar; bila berulang, hubungi admin.", icon=":material/error:")


def kpi(label: str, value: str, hint: str = "", *, warn: bool = False) -> None:
    st.markdown(
        f'<div class="kpi{" warn" if warn else ""}"><div class="l">{esc(label)}</div>'
        f'<div class="v">{esc(value)}</div><div class="h">{esc(hint)}</div></div>',
        unsafe_allow_html=True,
    )


def brand_header(subtitle: str) -> str:
    return f'<div class="hg-brand">{BRAND_SVG}<div><b>Holy Grail</b><span>{esc(subtitle)}</span></div></div>'
