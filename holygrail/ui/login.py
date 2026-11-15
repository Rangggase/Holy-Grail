"""Halaman masuk staf."""

from __future__ import annotations

import time

import streamlit as st

from ..config import get_settings
from ..errors import AuthError
from ..security import LoginThrottle
from ..services import auth
from .components import brand_header, show_error


def render(engine) -> None:
    settings = get_settings()
    st.session_state.setdefault("throttle", LoginThrottle(settings.max_login_attempts, settings.lockout_seconds))
    throttle: LoginThrottle = st.session_state["throttle"]

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(brand_header(settings.store_name), unsafe_allow_html=True)
        st.markdown("# Masuk")
        st.caption("Gunakan akun staf yang diberikan admin.")
        with st.form("login", border=True):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Masuk", type="primary", use_container_width=True)
        if not submitted:
            return
        now = time.time()
        if throttle.is_locked(now):
            st.error(f"Terlalu banyak percobaan. Coba lagi dalam {throttle.remaining_lock(now)} detik.", icon=":material/lock:")
            return
        if not username.strip() or not password:
            st.warning("Isi username dan password.", icon=":material/info:")
            return
        try:
            staff = auth.authenticate(engine, username, password)
        except AuthError as exc:
            throttle.record_failure(now)
            st.error(str(exc), icon=":material/error:")
            return
        except Exception as exc:  # noqa: BLE001 - tampilkan pesan ramah
            show_error(exc)
            return
        throttle.record_success()
        st.session_state["staff"] = staff
        st.session_state["page"] = "kasir"
        st.rerun()
