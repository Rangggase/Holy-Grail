"""Holy Grail POS — entry point Streamlit.  Jalankan: streamlit run app.py"""

import streamlit as st
from sqlalchemy import inspect

from holygrail.config import get_settings
from holygrail.db import make_engine
from holygrail.ui import admin, kasir, login, theme
from holygrail.ui.components import brand_header, show_error

st.set_page_config(page_title="Holy Grail POS", page_icon=":material/restaurant:", layout="wide", initial_sidebar_state="collapsed")
theme.inject()


@st.cache_resource(show_spinner=False)
def get_engine(url: str):
    return make_engine(url)


def _logout() -> None:
    for key in ("staff", "cart", "receipt", "idem", "cash", "page"):
        st.session_state.pop(key, None)


def _go(page: str) -> None:
    st.session_state["page"] = page


def main() -> None:
    settings = get_settings()
    try:
        engine = get_engine(settings.database_url)
        ready = inspect(engine).has_table("staff")
    except Exception as exc:  # noqa: BLE001
        show_error(exc)
        st.stop()
    if not ready:
        st.error("Database belum disiapkan. Jalankan perintah berikut di terminal, lalu muat ulang halaman:", icon=":material/database:")
        st.code("python -m scripts.init_db --demo", language="bash")
        st.stop()

    staff = st.session_state.get("staff")
    if staff is None:
        login.render(engine)
        return

    page = st.session_state.get("page", "kasir")
    if page == "admin" and staff.role != "admin":
        page = "kasir"

    left, right = st.columns([3, 4])
    with left:
        st.markdown(brand_header(settings.store_name), unsafe_allow_html=True)
    with right:
        cols = st.columns([1.2, 1.2, 1.6, 1.1] if staff.role == "admin" else [1.2, 1.6, 1.1])
        i = 0
        cols[i].button("Kasir", icon=":material/point_of_sale:", type="primary" if page == "kasir" else "secondary",
                       use_container_width=True, on_click=_go, args=("kasir",), key="nav_kasir")
        i += 1
        if staff.role == "admin":
            cols[i].button("Admin", icon=":material/monitoring:", type="primary" if page == "admin" else "secondary",
                           use_container_width=True, on_click=_go, args=("admin",), key="nav_admin")
            i += 1
        cols[i].caption(f"Masuk sebagai {staff.full_name}")
        cols[i + 1].button("Keluar", icon=":material/logout:", use_container_width=True, on_click=_logout, key="nav_logout")

    if page == "admin":
        admin.render(engine, staff)
    else:
        kasir.render(engine, staff, settings.store_name)


main()
