"""Halaman admin: Dasbor Analitik (bento grid), Menu & Stok, Riwayat Transaksi."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..errors import HolyGrailError
from ..services import menu as menu_svc
from ..services import reports
from .components import badge, card_title, esc, kpi, number_id, rupiah, show_error
from .theme import SEGMENT_COLORS, TOKENS

PERIODS = {"7 hari": 7, "30 hari": 30, "90 hari": 90, "12 bulan": 365, "Semua": None}
BRAND, BRAND_MID, GRID = TOKENS["brand"], "#3A8F7B", "#E2E8F0"


def _style(fig: go.Figure, height: int = 280) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=4, r=36, t=8, b=4), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", color=TOKENS["ink"], size=12), showlegend=False,
        hoverlabel=dict(font_size=12, bgcolor="#FFFFFF", font_color=TOKENS["ink"], bordercolor=TOKENS["line_strong"]),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, automargin=True, tickfont=dict(color=TOKENS["ink_muted"]), title_font=dict(color=TOKENS["ink_muted"]))
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, automargin=True, tickfont=dict(color=TOKENS["ink_muted"]), title_font=dict(color=TOKENS["ink_muted"]))
    return fig


def _period(key: str) -> tuple[date, date, str]:
    label = st.segmented_control("Periode laporan", list(PERIODS), default="30 hari", key=key) or "30 hari"
    days, end = PERIODS[label], date.today()
    return (date(2000, 1, 1) if days is None else end - timedelta(days=days - 1)), end, label


def _load(engine, start: date, end: date) -> pd.DataFrame | None:
    try:
        return reports.sales_lines(engine, start, end)
    except HolyGrailError as exc:
        show_error(exc)
        return None


# ---------------------------------------------------------------- Dasbor
def render_dashboard(engine) -> None:
    start, end, label = _period("dash_period")
    lines = _load(engine, start, end)
    if lines is None:
        return
    k = reports.kpis(lines)
    if lines.empty:
        st.info("Belum ada transaksi pada periode ini. Coba pilih periode yang lebih panjang.", icon=":material/info:")

    with st.container(key="bento_kpi"):
        c = st.columns(4)
        with c[0]:
            kpi("Omzet", rupiah(k.revenue), f"Periode: {label.lower()}", icon_name="payments")
        with c[1]:
            kpi("Transaksi", number_id(k.transactions), f"{number_id(k.items_sold)} porsi terjual", icon_name="receipt_long")
        with c[2]:
            kpi("Rata-rata per transaksi", rupiah(k.avg_basket), "Nilai keranjang rata-rata", icon_name="shopping_basket")
        with c[3]:
            kpi("Menu terlaris", k.best_seller, "Berdasarkan jumlah terjual", icon_name="star", small=True)
    if lines.empty:
        return

    with st.container(key="bento_trend"):
        left, right = st.columns([2, 1])
        with left, st.container(border=True):
            daily = reports.daily_sales(lines)
            weekly = len(daily) > 100
            card_title("Tren omzet", "Per minggu (periode panjang)" if weekly else "Per hari")
            if weekly:
                daily = daily.set_index("tanggal").resample("W").agg({"omzet": "sum", "transaksi": "sum"}).reset_index()
            fig = px.area(daily, x="tanggal", y="omzet", labels={"tanggal": "", "omzet": "Omzet (Rp)"}, color_discrete_sequence=[BRAND])
            fig.update_traces(line_width=2.2, fillcolor="rgba(15,92,77,0.10)", hovertemplate="%{x|%d %b %Y}<br>Rp %{y:,.0f}<extra></extra>")
            st.plotly_chart(_style(fig, 300), use_container_width=True)
            peak = daily.loc[daily["omzet"].idxmax()]
            st.caption(f"Omzet tertinggi {rupiah(peak['omzet'])} pada {peak['tanggal']:%d %b %Y}.")
        with right, st.container(border=True):
            card_title("Produk terlaris", "Jumlah porsi terjual")
            top = reports.top_products(lines, 8).iloc[::-1].copy()
            top["label"] = top["menu"].map(lambda n: n if len(n) <= 18 else n[:17] + "…")  # nama penuh tetap muncul saat hover
            fig = px.bar(top, x="terjual", y="label", orientation="h", text="terjual", labels={"terjual": "Terjual", "label": ""},
                         color_discrete_sequence=[BRAND], custom_data=["menu"])
            fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{customdata[0]}: %{x} porsi<extra></extra>")
            fig.update_yaxes(tickfont=dict(size=11, color=TOKENS["ink"]))
            st.plotly_chart(_style(fig, 300), use_container_width=True)

    with st.container(key="bento_mid"):
        a, b, c = st.columns(3)
        with a, st.container(border=True):
            card_title("Jam sibuk", "Jumlah transaksi per jam")
            hourly = reports.hourly_sales(lines)
            peak_hours = set(hourly.nlargest(3, "transaksi")["jam"])
            fig = go.Figure(go.Bar(x=hourly["jam"], y=hourly["transaksi"], marker_color=[TOKENS["brand"] if h in peak_hours else BRAND_MID for h in hourly["jam"]],
                                   hovertemplate="Pukul %{x}:00<br>%{y} transaksi<extra></extra>"))
            fig.update_xaxes(dtick=3, title="Jam (00–23)")
            st.plotly_chart(_style(fig, 230), use_container_width=True)
            busiest = hourly.loc[hourly["transaksi"].idxmax()]
            st.caption(f"Tersibuk pukul {int(busiest['jam']):02d}:00 ({int(busiest['transaksi'])} transaksi). Batang tergelap = 3 jam teratas.")
        with b, st.container(border=True):
            card_title("Stok menipis", f"Menu aktif dengan stok ≤ {menu_svc.LOW_STOCK_THRESHOLD}")
            low = menu_svc.low_stock(engine)
            if low.empty:
                st.success("Semua stok aman.", icon=":material/check_circle:")
            else:
                rows = "".join(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);font-size:.86rem">'
                    f'<span>{esc(r.menu_name)}</span>{badge(("Habis" if r.stock <= 0 else f"Sisa {r.stock}"), "out" if r.stock <= 0 else "low")}</div>'
                    for r in low.head(7).itertuples()
                )
                st.markdown(rows, unsafe_allow_html=True)
                more = len(low) - 7
                st.caption(f"+{more} menu lain. Atur di Menu & Stok." if more > 0 else "Atur persediaan di Menu & Stok.")
        with c, st.container(border=True):
            card_title("Metode pembayaran", "Jumlah transaksi")
            mix = reports.payment_mix(lines)
            share = (mix["transaksi"] / mix["transaksi"].sum() * 100).round(1)
            fig = go.Figure(go.Bar(y=mix["metode"][::-1], x=mix["transaksi"][::-1], orientation="h", marker_color=BRAND,
                                   text=[f"{s:.0f}%" for s in share[::-1]], textposition="outside", cliponaxis=False,
                                   hovertemplate="%{y}: %{x} transaksi<extra></extra>"))
            st.plotly_chart(_style(fig, 230), use_container_width=True)
            st.caption(f"Terbanyak: {mix.iloc[0]['metode']} ({share.iloc[0]:.0f}% transaksi).")

    with st.container(border=True):
        seg = reports.customer_segments(lines)
        card_title("Segmentasi pelanggan", "Dikelompokkan dari total belanja dalam periode terpilih")
        order = [t[0] for t in reports.SEGMENT_TIERS]
        counts = seg["segmen"].value_counts().reindex(order).fillna(0).astype(int).reset_index()
        counts.columns = ["Segmen", "Pelanggan"]
        left, right = st.columns([3, 2], gap="large")
        with left:
            fig = px.bar(counts, x="Pelanggan", y="Segmen", orientation="h", text="Pelanggan", color="Segmen",
                         color_discrete_map=SEGMENT_COLORS, category_orders={"Segmen": order})
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(_style(fig, 250), use_container_width=True)
        with right:
            tiers = "".join(
                f'<div style="padding:4px 0;font-size:.85rem"><b>{esc(n)}</b> '
                f'<span style="color:var(--muted)">({"≥ " + esc(rupiah(m)) if m else "di bawah Silver"})</span><br>'
                f'<span style="color:var(--muted)">{esc(tip)}</span></div>'
                for n, m, tip in reports.SEGMENT_TIERS
            )
            st.markdown(tiers, unsafe_allow_html=True)
        top = seg.sort_values("total_belanja", ascending=False).head(10).rename(
            columns={"nama": "Nama", "total_belanja": "Total belanja", "jumlah_transaksi": "Transaksi", "segmen": "Segmen"})
        st.dataframe(top[["Nama", "Segmen", "Transaksi", "Total belanja"]], use_container_width=True, hide_index=True,
                     column_config={"Total belanja": st.column_config.NumberColumn(label="Total belanja (Rp)", format="localized")})


# ---------------------------------------------------------------- Menu & Stok
def render_menu(engine, staff) -> None:
    menu_all = menu_svc.list_menu(engine, active_only=False)
    names = {f"{r.menu_name} — {r.category}": r for r in menu_all.itertuples()}

    left, right = st.columns([3, 2], gap="medium")
    with left, st.container(border=True):
        card_title("Daftar menu", f"{len(menu_all)} menu terdaftar")
        c1, c2 = st.columns([2, 1])
        q = c1.text_input("Cari menu", key="menu_admin_q", placeholder="Cari nama menu", label_visibility="collapsed")
        cats = c2.selectbox("Kategori", ["Semua kategori"] + sorted(menu_all["category"].unique()), key="menu_admin_cat", label_visibility="collapsed")
        view = menu_all
        if q.strip():
            view = view[view["menu_name"].str.contains(q.strip(), case=False, regex=False)]
        if cats != "Semua kategori":
            view = view[view["category"] == cats]
        shown = view.rename(columns={"menu_name": "Menu", "category": "Kategori", "price": "Harga", "stock": "Stok", "is_active": "Aktif"})
        shown["Aktif"] = shown["Aktif"].map({1: "Ya", 0: "Tidak"})
        st.dataframe(shown.drop(columns=["menu_id"]), use_container_width=True, hide_index=True, height=520,
                     column_config={"Harga": st.column_config.NumberColumn(label="Harga (Rp)", format="localized")})
        st.caption(f"Menampilkan {number_id(len(shown))} dari {number_id(len(menu_all))} menu.")

    with right, st.container(border=True):
        low = menu_all[(menu_all["is_active"] == 1) & (menu_all["stock"] <= menu_svc.LOW_STOCK_THRESHOLD)]
        if not low.empty:
            st.warning(f"{len(low)} menu bersisa ≤ {menu_svc.LOW_STOCK_THRESHOLD}: " + ", ".join(f"{r.menu_name} ({r.stock})" for r in low.head(5).itertuples())
                       + (" …" if len(low) > 5 else ""), icon=":material/inventory:")
        t1, t2, t3 = st.tabs(["Stok", "Ubah menu", "Tambah menu"])
        with t1:
            with st.form("form_stock", clear_on_submit=True, border=False):
                sel = st.selectbox("Menu", list(names), key="stock_menu")
                delta = st.number_input("Jumlah (positif = tambah, negatif = kurang)", value=0, step=1, key="stock_delta")
                reason = st.radio("Alasan", ["Restok", "Koreksi"], horizontal=True)
                note = st.text_input("Catatan (opsional)", max_chars=200)
                if st.form_submit_button("Simpan stok", type="primary", icon=":material/save:", use_container_width=True):
                    try:
                        new = menu_svc.adjust_stock(engine, int(names[sel].menu_id), int(delta),
                                                    reason="restock" if reason == "Restok" else "adjustment", staff_id=staff.staff_id, note=note)
                        st.success(f"Stok diperbarui. Sekarang: {new}.", icon=":material/check_circle:")
                    except Exception as exc:  # noqa: BLE001
                        show_error(exc)
        with t2:
            sel2 = st.selectbox("Pilih menu", list(names), key="edit_menu")
            cur = names[sel2]
            with st.form(f"form_edit_{cur.menu_id}", border=False):
                name = st.text_input("Nama menu", value=cur.menu_name, max_chars=80)
                cat = st.text_input("Kategori", value=cur.category, max_chars=40)
                price = st.number_input("Harga (Rp)", min_value=1, value=int(cur.price), step=500)
                active = st.checkbox("Tampil di kasir", value=bool(cur.is_active))
                if st.form_submit_button("Simpan perubahan", type="primary", icon=":material/save:", use_container_width=True):
                    try:
                        menu_svc.update_menu(engine, int(cur.menu_id), name=name, category=cat, price=price, is_active=active)
                        st.success("Menu diperbarui. Riwayat transaksi lama tidak berubah.", icon=":material/check_circle:")
                    except Exception as exc:  # noqa: BLE001
                        show_error(exc)
        with t3:
            with st.form("form_add", clear_on_submit=True, border=False):
                n = st.text_input("Nama menu", max_chars=80, key="new_name")
                cat = st.text_input("Kategori", max_chars=40, key="new_cat", placeholder="mis. Makanan Berat")
                c1, c2 = st.columns(2)
                p = c1.number_input("Harga (Rp)", min_value=1, value=10000, step=500, key="new_price")
                s = c2.number_input("Stok awal", min_value=0, value=0, step=1, key="new_stock")
                if st.form_submit_button("Tambah menu", type="primary", icon=":material/add:", use_container_width=True):
                    try:
                        menu_svc.add_menu(engine, name=n, category=cat, price=p, stock=s, staff_id=staff.staff_id)
                        st.success(f"Menu '{n.strip()}' ditambahkan.", icon=":material/check_circle:")
                    except Exception as exc:  # noqa: BLE001
                        show_error(exc)


# ---------------------------------------------------------------- Riwayat
def render_history(engine) -> None:
    start, end, _ = _period("hist_period")
    lines = _load(engine, start, end)
    if lines is None:
        return
    table = reports.transaction_table(lines)
    if table.empty:
        st.info("Belum ada transaksi pada periode ini.", icon=":material/receipt_long:")
        return
    with st.container(border=True):
        c1, c2 = st.columns([2, 2])
        cats = c1.multiselect("Kategori", sorted(table["Kategori"].unique()), placeholder="Semua kategori", key="hist_cat")
        who = c2.text_input("Pelanggan", placeholder="Cari nama pelanggan", key="hist_who")
        shown = table[table["Kategori"].isin(cats)] if cats else table
        if who.strip():
            shown = shown[shown["Pelanggan"].str.contains(who.strip(), case=False, regex=False)]
        n_trx, total = shown["No. Transaksi"].nunique(), int(shown["Subtotal"].sum())
        m1, m2, m3 = st.columns(3)
        with m1:
            kpi("Baris item", number_id(len(shown)), "Sesuai filter", icon_name="list")
        with m2:
            kpi("Transaksi", number_id(n_trx), "Struk unik", icon_name="receipt_long")
        with m3:
            kpi("Nilai", rupiah(total), "Jumlah subtotal", icon_name="payments")
        st.dataframe(shown.head(2000), use_container_width=True, hide_index=True, height=480,
                     column_config={"Harga Satuan": st.column_config.NumberColumn(label="Harga Satuan (Rp)", format="localized"), "Subtotal": st.column_config.NumberColumn(label="Subtotal (Rp)", format="localized")})
        if len(shown) > 2000:
            st.caption("Tabel dibatasi 2.000 baris teratas; unduhan CSV memuat semua baris.")
        st.download_button("Unduh CSV", reports.to_safe_csv(shown), file_name="laporan-penjualan-holygrail.csv", mime="text/csv",
                           type="primary", icon=":material/download:")
