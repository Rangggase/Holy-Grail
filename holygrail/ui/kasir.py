"""Layar kasir: pilih menu, keranjang, pembayaran, nota."""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from .. import db
from ..errors import HolyGrailError
from ..validation import MAX_PAYMENT
from ..services import checkout as checkout_svc
from ..services import customers as customer_svc
from ..services import menu as menu_svc
from ..services import recommender
from .components import esc, number_id, rupiah, show_error

QUICK_CASH = (50_000, 100_000, 200_000)


# ---------- keranjang (state hanya menyimpan menu_id -> qty; harga selalu dari DB) ----------
def _cart() -> dict[int, int]:
    return st.session_state.setdefault("cart", {})


def _stock_of(menu_id: int) -> int:
    return int(st.session_state.get("_stock", {}).get(menu_id, 0))


def _add(menu_id: int) -> None:
    cart = _cart()
    if cart.get(menu_id, 0) >= _stock_of(menu_id):
        st.toast("Stok tidak cukup untuk menambah lagi.", icon=":material/warning:")
        return
    cart[menu_id] = cart.get(menu_id, 0) + 1


def _dec(menu_id: int) -> None:
    cart = _cart()
    if cart.get(menu_id, 0) <= 1:
        cart.pop(menu_id, None)
    else:
        cart[menu_id] -= 1


def _remove(menu_id: int) -> None:
    _cart().pop(menu_id, None)


def _set_cash(amount: int) -> None:
    st.session_state["cash"] = amount


def _new_sale() -> None:
    st.session_state["receipt"] = None
    st.session_state["cart"] = {}
    st.session_state["idem"] = uuid.uuid4().hex
    st.session_state["cash"] = 0


@st.cache_data(ttl=120, show_spinner=False)
def _history(_engine, cache_key: str) -> pd.DataFrame:
    return recommender.load_history(_engine)


def _receipt_text(r: checkout_svc.Receipt, store: str) -> str:
    lines = [store, r.created_at.strftime("%Y-%m-%d %H:%M"), f"No. {r.trx_id}  Pelanggan: {r.customer_name}", "-" * 32]
    lines += [f"{l.qty}x {l.menu_name}\n    {number_id(l.subtotal):>26}" for l in r.lines]
    lines += ["-" * 32, f"TOTAL  {rupiah(r.total)}", f"Bayar ({r.payment_method})  {rupiah(r.paid)}", f"Kembali  {rupiah(r.change)}", "Terima kasih!"]
    return "\n".join(lines)


def _render_receipt(r: checkout_svc.Receipt, store: str) -> None:
    rows = "".join(
        f'<div class="row"><span>{l.qty}x {esc(l.menu_name)}</span><span>{number_id(l.subtotal)}</span></div>' for l in r.lines
    )
    st.markdown(
        f"""<div class="nota"><h4>{esc(store)}</h4>
        <div class="meta">{esc(r.created_at.strftime('%d %b %Y, %H:%M'))} &middot; No. {r.trx_id}</div>
        <div class="meta">Pelanggan: {esc(r.customer_name)}</div><hr>{rows}<hr>
        <div class="row total"><span>TOTAL</span><span>{rupiah(r.total)}</span></div>
        <div class="row"><span>Bayar ({esc(r.payment_method)})</span><span>{number_id(r.paid)}</span></div>
        <div class="row"><span>Kembali</span><span>{number_id(r.change)}</span></div>
        <div class="thanks">Terima kasih!</div></div>""",
        unsafe_allow_html=True,
    )
    st.download_button("Unduh nota (.txt)", _receipt_text(r, store), file_name=f"nota-{r.trx_id}.txt", icon=":material/download:", use_container_width=True)
    st.button("Transaksi baru", type="primary", icon=":material/add_circle:", use_container_width=True, on_click=_new_sale, key="btn_new_sale")


# ---------- bagian layar ----------
def _context_panel(engine) -> tuple[str, int | None, str, str, str]:
    st.markdown("### Pesanan")
    with st.container(key="grid_ctx"):
        c1, c2, c3 = st.columns([2.2, 1.4, 1.4])
        with c1:
            typed = st.text_input("Nama pelanggan", key="cust_name", placeholder="Ketik nama pelanggan", max_chars=60)
        with c2:
            weather = st.segmented_control("Cuaca", db.WEATHERS, default="Cerah", key="ctx_weather") or "Cerah"
        with c3:
            group = st.segmented_control("Rombongan", db.GROUP_SIZES, default="Sendiri", key="ctx_group") or "Sendiri"

    name, customer_id = " ".join(typed.split()), None
    if len(name) >= 2:
        matches = customer_svc.search_customers(engine, name)
        exact = next((m for m in matches if m.name.lower() == name.lower()), None)
        if exact:
            name, customer_id = exact.name, exact.customer_id
            st.caption(f"Member terdaftar: {exact.name}")
        elif matches:
            new_label = f"Pelanggan baru: {name}"
            pick = st.selectbox("Mungkin pelanggan ini?", [new_label] + [m.name for m in matches], key="cust_pick")
            if pick != new_label:
                chosen = next(m for m in matches if m.name == pick)
                name, customer_id = chosen.name, chosen.customer_id
        else:
            st.caption("Pelanggan baru — akan didaftarkan saat pembayaran.")
    tod = checkout_svc.time_of_day(datetime.now().hour)
    st.caption(f"Waktu: {tod.lower()}")
    return name, customer_id, weather, group, tod


def _suggestions(engine, menu_df, customer_id, weather, group, tod) -> None:
    hist = _history(engine, str(engine.url))
    rec = recommender.recommend(menu_df, hist, weather=weather, group_size=group, time_of_day=tod, customer_id=customer_id, top_n=40)
    if rec.empty:
        return
    st.markdown("### Saran menu")
    st.caption("Berdasarkan aturan cuaca & rombongan serta riwayat penjualan — bukan prediksi pasti.")
    for title, is_drink in (("Makanan", False), ("Minuman", True)):
        sub = rec[(rec["category"] == "Minuman") == is_drink].head(4)
        if sub.empty:
            continue
        st.markdown(f"**{title}**")
        with st.container(key=f"grid_rec_{int(is_drink)}"):
            cols = st.columns(4)
            for col, row in zip(cols, sub.itertuples()):
                with col, st.container(border=True):
                    st.markdown(
                        f'<div class="menu-name">{esc(row.menu_name)}</div><div class="price">{rupiah(row.price)}</div>'
                        f'<div class="reason">{esc(" · ".join(row.reasons[:2]))}</div>',
                        unsafe_allow_html=True,
                    )
                    st.button("Tambah", key=f"rec_{row.menu_id}", on_click=_add, args=(int(row.menu_id),), icon=":material/add:", use_container_width=True)


def _menu_grid(menu_df: pd.DataFrame) -> None:
    st.markdown("### Buku menu")
    q = st.text_input("Cari menu", key="menu_search", placeholder="Ketik nama menu", max_chars=60)
    cats = sorted(menu_df["category"].unique().tolist())
    if "Paket Jumbo" in cats:
        cats.remove("Paket Jumbo")
        cats.insert(0, "Paket Jumbo")
    tabs = st.tabs(cats)
    cart = _cart()
    for ci, (tab, cat) in enumerate(zip(tabs, cats)):
        with tab:
            part = menu_df[menu_df["category"] == cat]
            if q.strip():
                part = part[part["menu_name"].str.contains(q.strip(), case=False, regex=False)]
            if part.empty:
                st.info("Tidak ada menu yang cocok. Coba kata kunci lain.", icon=":material/search_off:")
                continue
            for start in range(0, len(part), 3):
                with st.container(key=f"grid_menu_{ci}_{start}"):
                    cols = st.columns(3)
                    for col, row in zip(cols, part.iloc[start : start + 3].itertuples()):
                        left = int(row.stock) - cart.get(int(row.menu_id), 0)
                        with col, st.container(border=True):
                            badge = '<span class="badge low">Habis</span>' if row.stock <= 0 else (
                                f'<span class="badge low">Sisa {row.stock}</span>' if row.stock <= menu_svc.LOW_STOCK_THRESHOLD else f'<span class="badge">Stok {row.stock}</span>')
                            st.markdown(
                                f'<div class="menu-name">{esc(row.menu_name)}</div><div class="price">{rupiah(row.price)}</div>{badge}',
                                unsafe_allow_html=True,
                            )
                            st.button("Tambah", key=f"add_{row.menu_id}", on_click=_add, args=(int(row.menu_id),), icon=":material/add:",
                                      use_container_width=True, disabled=left <= 0)


def _cart_panel(engine, staff, menu_df, name, weather, group, store) -> None:
    cart = _cart()
    by_id = menu_df.set_index("menu_id")
    # Buang item yang sudah tidak aktif / melebihi stok terbaru.
    for mid in list(cart):
        if mid not in by_id.index:
            cart.pop(mid)
        elif cart[mid] > by_id.at[mid, "stock"]:
            cart[mid] = int(by_id.at[mid, "stock"])
            if cart[mid] <= 0:
                cart.pop(mid)

    st.markdown("### Keranjang")
    if not cart:
        st.info("Keranjang masih kosong. Pilih menu di sebelah kiri.", icon=":material/shopping_cart:")
        return
    total = 0
    for mid, qty in cart.items():
        price = int(by_id.at[mid, "price"])
        total += price * qty
        with st.container(border=True):
            c0, c1, c2, c3 = st.columns([2.4, 1, 1, 1], vertical_alignment="center")
            c0.markdown(f'<div class="menu-name" style="min-height:0">{esc(by_id.at[mid, "menu_name"])}</div>'
                        f'<div class="reason" style="min-height:0">{qty} &times; {rupiah(price)} = <b>{rupiah(price * qty)}</b></div>', unsafe_allow_html=True)
            c1.button("", key=f"dec_{mid}", on_click=_dec, args=(mid,), icon=":material/remove:", use_container_width=True, help="Kurangi satu")
            c2.button("", key=f"inc_{mid}", on_click=_add, args=(mid,), icon=":material/add:", use_container_width=True, help="Tambah satu")
            c3.button("", key=f"del_{mid}", on_click=_remove, args=(mid,), icon=":material/delete:", use_container_width=True, help="Hapus dari keranjang")

    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:baseline"><span>Total</span><span class="total-big">{rupiah(total)}</span></div>', unsafe_allow_html=True)
    method = st.radio("Metode pembayaran", db.PAYMENT_METHODS, horizontal=True, key="pay_method")
    paid = total
    if method == "Tunai":
        st.number_input("Uang diterima (Rp)", min_value=0, max_value=MAX_PAYMENT, step=1000, key="cash")
        q1, q2, q3, q4 = st.columns(4)
        q1.button("Pas", on_click=_set_cash, args=(total,), use_container_width=True, key="q_pas")
        for col, amt in zip((q2, q3, q4), QUICK_CASH):
            col.button(f"{amt // 1000}rb", on_click=_set_cash, args=(amt,), use_container_width=True, key=f"q_{amt}")
        paid = int(st.session_state.get("cash", 0))
        if paid >= total:
            st.success(f"Kembalian {rupiah(paid - total)}", icon=":material/payments:")
        elif paid > 0:
            st.warning(f"Uang kurang {rupiah(total - paid)}", icon=":material/warning:")
    else:
        st.caption("Pembayaran non-tunai dicatat sebesar total belanja.")

    can_pay = bool(name) and (method != "Tunai" or paid >= total)
    if not name:
        st.caption("Isi nama pelanggan untuk melanjutkan.")
    if st.button("Bayar", type="primary", icon=":material/check_circle:", use_container_width=True, disabled=not can_pay, key="btn_pay"):
        try:
            receipt = checkout_svc.checkout(
                engine, lines=list(cart.items()), customer_name=name, payment_method=method, paid=paid,
                weather=weather, group_size=group, cashier_id=staff.staff_id, idempotency_key=st.session_state["idem"],
            )
        except HolyGrailError as exc:
            show_error(exc)
        except Exception as exc:  # noqa: BLE001
            show_error(exc)
        else:
            st.session_state["receipt"] = receipt
            st.session_state["cart"] = {}
            _history.clear()
            st.rerun()


def render(engine, staff, store: str) -> None:
    st.session_state.setdefault("idem", uuid.uuid4().hex)
    st.session_state.setdefault("receipt", None)
    st.session_state.setdefault("cash", 0)
    menu_df = menu_svc.list_menu(engine)
    st.session_state["_stock"] = {int(r.menu_id): int(r.stock) for r in menu_df.itertuples()}
    st.title("Kasir")

    main, side = st.columns([5, 2.6], gap="large")
    with main:
        name, customer_id, weather, group, tod = _context_panel(engine)
        if menu_df.empty:
            st.warning("Belum ada menu aktif. Minta admin menambahkan menu.", icon=":material/restaurant_menu:")
        else:
            _suggestions(engine, menu_df, customer_id, weather, group, tod)
            _menu_grid(menu_df)
    with side, st.container(key="nota"):
        receipt = st.session_state.get("receipt")
        if receipt is not None:
            st.success("Pembayaran berhasil.", icon=":material/check_circle:")
            _render_receipt(receipt, store)
        else:
            _cart_panel(engine, staff, menu_df, name, weather, group, store)
