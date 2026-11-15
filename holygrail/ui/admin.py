"""Dasbor admin: ringkasan, pelanggan, menu & stok, transaksi."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..errors import HolyGrailError
from ..services import menu as menu_svc
from ..services import reports
from .components import esc, kpi, number_id, rupiah, show_error
from .theme import SEGMENT_COLORS, TOKENS

PERIODS = {"7 hari": 7, "30 hari": 30, "90 hari": 90, "12 bulan": 365, "Semua": None}


def _style(fig: go.Figure, height: int = 330) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=24, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", color=TOKENS["ink"], size=13),
        legend=dict(orientation="h", y=-0.2), hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(gridcolor="#DDE4E0", linecolor=TOKENS["line"], zeroline=False)
    fig.update_yaxes(gridcolor="#DDE4E0", linecolor=TOKENS["line"], zeroline=False)
    return fig


def _period() -> tuple[date, date]:
    label = st.segmented_control("Periode laporan", list(PERIODS), default="30 hari", key="admin_period") or "30 hari"
    days = PERIODS[label]
    end = date.today()
    return (date(2000, 1, 1) if days is None else end - timedelta(days=days - 1)), end


def _overview(lines: pd.DataFrame, engine) -> None:
    k = reports.kpis(lines)
    low = menu_svc.low_stock(engine)
    c = st.columns(5)
    with c[0]:
        kpi("Omzet", rupiah(k.revenue), "Total penjualan periode ini")
    with c[1]:
        kpi("Transaksi", number_id(k.transactions), "Jumlah struk")
    with c[2]:
        kpi("Rata-rata per transaksi", rupiah(k.avg_basket), f"{number_id(k.items_sold)} porsi terjual")
    with c[3]:
        kpi("Menu terlaris", k.best_seller, "Berdasarkan jumlah terjual")
    with c[4]:
        kpi("Stok menipis", number_id(len(low)), "Menu dengan stok ≤ 10", warn=len(low) > 0)
    if lines.empty:
        st.info("Belum ada transaksi pada periode ini. Coba pilih periode yang lebih panjang.", icon=":material/info:")
        return

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Omzet harian")
        daily = reports.daily_sales(lines)
        if len(daily) > 100:  # ringkas ke mingguan agar grafik tetap terbaca
            daily = daily.set_index("tanggal").resample("W").agg({"omzet": "sum", "transaksi": "sum"}).reset_index()
            st.caption("Ditampilkan per minggu karena periode panjang.")
        fig = px.area(daily, x="tanggal", y="omzet", labels={"tanggal": "Tanggal", "omzet": "Omzet (Rp)"}, color_discrete_sequence=[TOKENS["brand"]])
        fig.update_traces(line_width=2.5, fillcolor="rgba(15,92,77,0.15)", hovertemplate="%{x|%d %b %Y}<br>Rp %{y:,.0f}<extra></extra>")
        st.plotly_chart(_style(fig), use_container_width=True)
    with right:
        st.markdown("### Jam sibuk")
        hourly = reports.hourly_sales(lines)
        fig = px.bar(hourly, x="jam", y="transaksi", labels={"jam": "Jam (00–23)", "transaksi": "Jumlah transaksi"}, color_discrete_sequence=[TOKENS["brand"]])
        fig.update_xaxes(dtick=2)
        fig.update_traces(hovertemplate="Pukul %{x}:00<br>%{y} transaksi<extra></extra>")
        st.plotly_chart(_style(fig), use_container_width=True)

    f, d = st.columns(2, gap="large")
    for col, title, drinks in ((f, "Makanan terlaris", False), (d, "Minuman terlaris", True)):
        with col:
            st.markdown(f"### {title}")
            top = reports.top_menu(lines, drinks=drinks)
            if top.empty:
                st.caption("Belum ada data.")
                continue
            fig = px.bar(top.iloc[::-1], x="terjual", y="menu", orientation="h", text="terjual", labels={"terjual": "Terjual", "menu": ""},
                         color_discrete_sequence=[TOKENS["brand"] if not drinks else "#2F7F8F"])
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(_style(fig, 280), use_container_width=True)
            with st.expander("Lihat sebagai tabel"):
                st.dataframe(top.rename(columns={"menu": "Menu", "terjual": "Terjual", "omzet": "Omzet"}), use_container_width=True, hide_index=True)


def _customers(lines: pd.DataFrame) -> None:
    seg = reports.customer_segments(lines)
    if seg.empty:
        st.info("Belum ada data pelanggan pada periode ini.", icon=":material/group:")
        return
    order = [t[0] for t in reports.SEGMENT_TIERS]
    counts = seg["segmen"].value_counts().reindex(order).fillna(0).astype(int).reset_index()
    counts.columns = ["Segmen", "Pelanggan"]
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("### Segmen pelanggan")
        st.caption("Dikelompokkan dari total belanja dalam periode terpilih.")
        fig = px.bar(counts, x="Pelanggan", y="Segmen", orientation="h", text="Pelanggan", color="Segmen",
                     color_discrete_map=SEGMENT_COLORS, category_orders={"Segmen": order})
        fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(_style(fig, 300), use_container_width=True)
    with right:
        st.markdown("### Saran tindak lanjut")
        for name, minimum, tip in reports.SEGMENT_TIERS:
            rule = f"≥ {rupiah(minimum)}" if minimum else "di bawah Silver"
            st.markdown(f"**{name}** ({rule}): {tip}")
    st.markdown("### Pelanggan teratas")
    top = seg.sort_values("total_belanja", ascending=False).head(20).rename(
        columns={"nama": "Nama", "total_belanja": "Total belanja", "jumlah_transaksi": "Transaksi", "segmen": "Segmen"})
    st.dataframe(top[["Nama", "Segmen", "Transaksi", "Total belanja"]], use_container_width=True, hide_index=True,
                 column_config={"Total belanja": st.column_config.NumberColumn(format="Rp %d")})


def _menu_stock(engine, staff) -> None:
    menu_all = menu_svc.list_menu(engine, active_only=False)
    low = menu_all[(menu_all["is_active"] == 1) & (menu_all["stock"] <= menu_svc.LOW_STOCK_THRESHOLD)]
    if not low.empty:
        st.warning("Stok menipis: " + ", ".join(f"{r.menu_name} ({r.stock})" for r in low.itertuples()), icon=":material/inventory:")
    names = {f"{r.menu_name} — {r.category}": r for r in menu_all.itertuples()}
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("### Penyesuaian stok")
        with st.form("form_stock", clear_on_submit=True):
            sel = st.selectbox("Menu", list(names), key="stock_menu")
            delta = st.number_input("Jumlah (positif = tambah, negatif = kurang)", value=0, step=1, key="stock_delta")
            reason = st.radio("Alasan", ["Restok", "Koreksi"], horizontal=True)
            note = st.text_input("Catatan (opsional)", max_chars=200)
            if st.form_submit_button("Simpan stok", type="primary", icon=":material/save:"):
                try:
                    new = menu_svc.adjust_stock(engine, int(names[sel].menu_id), int(delta),
                                                reason="restock" if reason == "Restok" else "adjustment", staff_id=staff.staff_id, note=note)
                    st.success(f"Stok diperbarui. Sekarang: {new}.", icon=":material/check_circle:")
                except Exception as exc:  # noqa: BLE001
                    show_error(exc)
    with b:
        st.markdown("### Ubah menu")
        sel2 = st.selectbox("Pilih menu", list(names), key="edit_menu")
        cur = names[sel2]
        with st.form(f"form_edit_{cur.menu_id}"):
            name = st.text_input("Nama menu", value=cur.menu_name, max_chars=80)
            cat = st.text_input("Kategori", value=cur.category, max_chars=40)
            price = st.number_input("Harga (Rp)", min_value=1, value=int(cur.price), step=500)
            active = st.checkbox("Tampil di kasir", value=bool(cur.is_active))
            if st.form_submit_button("Simpan perubahan", type="primary", icon=":material/save:"):
                try:
                    menu_svc.update_menu(engine, int(cur.menu_id), name=name, category=cat, price=price, is_active=active)
                    st.success("Menu diperbarui. Riwayat transaksi lama tidak berubah.", icon=":material/check_circle:")
                except Exception as exc:  # noqa: BLE001
                    show_error(exc)
    with st.expander("Tambah menu baru"):
        with st.form("form_add", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nama menu", max_chars=80, key="new_name")
            cat = c2.text_input("Kategori", max_chars=40, key="new_cat", placeholder="mis. Makanan Berat")
            p = c1.number_input("Harga (Rp)", min_value=1, value=10000, step=500, key="new_price")
            s = c2.number_input("Stok awal", min_value=0, value=0, step=1, key="new_stock")
            if st.form_submit_button("Tambah menu", type="primary", icon=":material/add:"):
                try:
                    menu_svc.add_menu(engine, name=n, category=cat, price=p, stock=s, staff_id=staff.staff_id)
                    st.success(f"Menu '{n.strip()}' ditambahkan.", icon=":material/check_circle:")
                except Exception as exc:  # noqa: BLE001
                    show_error(exc)
    st.markdown("### Daftar menu")
    view = menu_svc.list_menu(engine, active_only=False).rename(
        columns={"menu_name": "Menu", "category": "Kategori", "price": "Harga", "stock": "Stok", "is_active": "Aktif"})
    view["Aktif"] = view["Aktif"].map({1: "Ya", 0: "Tidak"})
    st.dataframe(view.drop(columns=["menu_id"]), use_container_width=True, hide_index=True,
                 column_config={"Harga": st.column_config.NumberColumn(format="Rp %d")})


def _transactions(lines: pd.DataFrame) -> None:
    table = reports.transaction_table(lines)
    if table.empty:
        st.info("Belum ada transaksi pada periode ini.", icon=":material/receipt_long:")
        return
    cats = st.multiselect("Filter kategori", sorted(table["Kategori"].unique()), placeholder="Semua kategori")
    shown = table[table["Kategori"].isin(cats)] if cats else table
    st.caption(f"Menampilkan {number_id(len(shown))} baris item transaksi.")
    st.dataframe(shown.head(2000), use_container_width=True, hide_index=True,
                 column_config={"Harga Satuan": st.column_config.NumberColumn(format="Rp %d"), "Subtotal": st.column_config.NumberColumn(format="Rp %d")})
    if len(shown) > 2000:
        st.caption("Tabel dibatasi 2.000 baris teratas; unduhan CSV memuat semua baris.")
    st.download_button("Unduh CSV", reports.to_safe_csv(shown), file_name="laporan-penjualan-holygrail.csv", mime="text/csv",
                       type="primary", icon=":material/download:")


def render(engine, staff) -> None:
    st.title("Dasbor admin")
    start, end = _period()
    try:
        lines = reports.sales_lines(engine, start, end)
    except HolyGrailError as exc:
        show_error(exc)
        return
    t1, t2, t3, t4 = st.tabs(["Ringkasan", "Pelanggan", "Menu & stok", "Transaksi"])
    with t1:
        _overview(lines, engine)
    with t2:
        _customers(lines)
    with t3:
        _menu_stock(engine, staff)
    with t4:
        _transactions(lines)
