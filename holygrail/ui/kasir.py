"""Layar kasir (POS Terminal): split-screen produk (kiri 65%) + pesanan sticky (kanan 35%)."""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import streamlit as st

from .. import db
from ..errors import HolyGrailError
from ..services import checkout as checkout_svc
from ..services import customers as customer_svc
from ..services import menu as menu_svc
from ..services import recommender
from ..validation import MAX_PAYMENT
from .components import badge, card_title, esc, number_id, rupiah, show_error

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
        cart.pop(menu_id, None)  # kurangi dari 1 = hapus dari keranjang
    else:
        cart[menu_id] -= 1


def _clear_cart() -> None:
    st.session_state["cart"] = {}


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


# ---------- nota ----------
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


# ---------- kolom kiri ----------
def _context_panel(engine) -> tuple[str, int | None, str, str, str]:
    with st.container(border=True, key="grid_ctx"):
        c1, c2, c3 = st.columns([2.2, 1.3, 1.5])
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
    return name, customer_id, weather, group, checkout_svc.time_of_day(datetime.now().hour)


def _product_card(row, in_cart: int, key: str, *, reasons: list[str] | None = None) -> None:
    left = int(row.stock) - in_cart
    if row.stock <= 0:
        stock_badge = badge("Habis", "out")
    elif row.stock <= menu_svc.LOW_STOCK_THRESHOLD:
        stock_badge = badge(f"Sisa {row.stock}", "low")
    else:
        stock_badge = badge(f"Stok {row.stock}", "")
    in_cart_html = f" {badge(f'Di keranjang {in_cart}', 'neutral')}" if in_cart else ""
    reason_html = f'<div class="reason">{esc(" · ".join(reasons[:2]))}</div>' if reasons else ""
    with st.container(border=True):
        st.markdown(
            f'<div class="p-cat">{esc(row.category)}</div><div class="menu-name">{esc(row.menu_name)}</div>'
            f'<div class="p-row"><span class="price">{rupiah(row.price)}</span><span>{stock_badge}{in_cart_html}</span></div>{reason_html}',
            unsafe_allow_html=True,
        )
        st.button("Tambah", key=key, on_click=_add, args=(int(row.menu_id),), icon=":material/add:", use_container_width=True, disabled=left <= 0)


def _suggestions(engine, menu_df, customer_id, weather, group, tod) -> None:
    rec = recommender.recommend(menu_df, _history(engine, str(engine.url)), weather=weather, group_size=group,
                                time_of_day=tod, customer_id=customer_id, top_n=40)
    if rec.empty:
        return
    drinks = rec[rec["category"] == "Minuman"].head(2)
    picks = pd.concat([rec[rec["category"] != "Minuman"].head(4 - len(drinks)), drinks]).sort_values("score", ascending=False)
    by_id = menu_df.set_index("menu_id")
    cart = _cart()
    card_title("Saran menu", "Berdasarkan aturan cuaca & rombongan serta riwayat penjualan — bukan prediksi pasti.")
    with st.container(key="grid_rec"):
        for col, rec_row in zip(st.columns(4), picks.itertuples()):
            src = by_id.loc[rec_row.menu_id]
            row = SimpleNamespace(menu_id=rec_row.menu_id, menu_name=src["menu_name"], category=src["category"], price=src["price"], stock=src["stock"])
            with col:
                _product_card(row, cart.get(int(rec_row.menu_id), 0), f"rec_{rec_row.menu_id}", reasons=rec_row.reasons)


def _menu_grid(menu_df: pd.DataFrame) -> None:
    cats = sorted(menu_df["category"].unique().tolist())
    if "Paket Jumbo" in cats:
        cats.remove("Paket Jumbo")
        cats.insert(0, "Paket Jumbo")
    card_title("Buku menu", f"{len(menu_df)} menu aktif")
    q = st.text_input("Cari menu", key="menu_search", placeholder="Cari nama menu, lalu tekan Enter", max_chars=60, label_visibility="collapsed")
    chosen = st.pills("Kategori", ["Semua"] + cats, default="Semua", key="cat_filter", label_visibility="collapsed") or "Semua"

    part = menu_df.copy()
    part["_o"] = part["category"].map({c: i for i, c in enumerate(cats)})
    part = part.sort_values(["_o", "menu_name"])
    if chosen != "Semua":
        part = part[part["category"] == chosen]
    if q.strip():
        part = part[part["menu_name"].str.contains(q.strip(), case=False, regex=False)]
    if part.empty:
        st.info("Tidak ada menu yang cocok. Coba kata kunci atau kategori lain.", icon=":material/search_off:")
        return
    cart = _cart()
    for start in range(0, len(part), 3):
        with st.container(key=f"grid_menu_{start}"):
            for col, row in zip(st.columns(3), part.iloc[start : start + 3].itertuples()):
                with col:
                    _product_card(row, cart.get(int(row.menu_id), 0), f"add_{row.menu_id}")


# ---------- kolom kanan ----------
def _cart_panel(engine, staff, menu_df, name, weather, group) -> None:
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

    count = sum(cart.values())
    st.markdown(f'<div class="cart-head"><b>Pesanan</b>{badge(f"{count} item", "" if count else "neutral")}</div>', unsafe_allow_html=True)
    st.caption(f"Pelanggan: {name}" if name else "Isi nama pelanggan di panel kiri.")
    if not cart:
        st.info("Keranjang masih kosong. Pilih menu di sebelah kiri.", icon=":material/shopping_cart:")
        return

    total = 0
    for mid, qty in cart.items():
        price = int(by_id.at[mid, "price"])
        total += price * qty
        with st.container(border=True):
            st.markdown(f'<div class="cart-line">{esc(by_id.at[mid, "menu_name"])}</div><div class="cart-sub">{rupiah(price)} per porsi</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([1.1, 0.8, 1.1, 2.2], vertical_alignment="center")
            c1.button("−", key=f"dec_{mid}", on_click=_dec, args=(mid,), use_container_width=True, help="Kurangi satu (di angka 1 = hapus)")
            c2.markdown(f'<div class="qty">{qty}</div>', unsafe_allow_html=True)
            c3.button("+", key=f"inc_{mid}", on_click=_add, args=(mid,), use_container_width=True, help="Tambah satu")
            c4.markdown(f'<div class="line-total">{rupiah(price * qty)}</div>', unsafe_allow_html=True)
    st.button("Kosongkan keranjang", key="btn_clear", on_click=_clear_cart, icon=":material/delete_sweep:", use_container_width=True)

    st.markdown(
        f'<div class="sum-row"><span>Subtotal ({count} item)</span><span>{rupiah(total)}</span></div>'
        f'<div class="sum-row" style="align-items:center"><b style="color:var(--ink)">Total</b><span class="total-big">{rupiah(total)}</span></div>',
        unsafe_allow_html=True,
    )
    method = st.segmented_control("Metode pembayaran", db.PAYMENT_METHODS, default="Tunai", key="pay_method") or "Tunai"
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

    main, side = st.columns([65, 35], gap="medium")
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
            _cart_panel(engine, staff, menu_df, name, weather, group)
