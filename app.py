"""Holy Grail POS — entry point Streamlit.  Jalankan: streamlit run app.py"""

import streamlit as st
from sqlalchemy import inspect

from holygrail.config import get_settings
from holygrail.db import make_engine
from holygrail.ui import admin, kasir, login, shell, theme
from holygrail.ui.components import show_error

st.set_page_config(page_title="Holy Grail POS", page_icon=":material/restaurant:", layout="wide", initial_sidebar_state="expanded")
theme.inject()


@st.cache_resource(show_spinner=False)
def get_engine(url: str):
    return make_engine(url)


def main() -> None:
    settings = get_settings()
    try:
        engine = get_engine(settings.database_url)
        ready = inspect(engine).has_table("staff")
    except Exception as exc:  # noqa: BLE001
        show_error(exc)
        st.stop()
    if not ready:
        theme.hide_sidebar()
        st.error("Database belum disiapkan. Jalankan perintah berikut di terminal, lalu muat ulang halaman:", icon=":material/database:")
        st.code("python -m scripts.init_db --demo", language="bash")
        st.stop()

    staff = st.session_state.get("staff")
    if staff is None:
        login.render(engine)
        return

    requested = st.session_state.get("page") or st.query_params.get("hal")
    page = shell.resolve_page(requested, staff.role)  # kasir tidak bisa membuka halaman admin
    st.session_state["page"] = page

    shell.render_sidebar(engine, staff, settings, page)
    shell.render_top_bar(engine, staff, page)

    if page == "kasir":
        kasir.render(engine, staff, settings.store_name)
    elif page == "dashboard":
        admin.render_dashboard(engine)
    elif page == "menu":
        admin.render_menu(engine, staff)
    else:
        admin.render_history(engine)


main()
