"""Rekomendasi menu berbasis ATURAN + RIWAYAT transaksi (bukan model machine learning).

Skor = popularitas dalam konteks yang sama (cuaca, rombongan, waktu) + kebiasaan pelanggan
+ popularitas umum + bonus aturan (mis. kuah hangat saat hujan). Setiap rekomendasi membawa alasan yang bisa dibaca kasir.
"""

from __future__ import annotations

import re

import pandas as pd

# kata kunci (kata utuh, huruf kecil) -> tag
TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "paket": ("Sharing", "Keluarga"), "bucket": ("Sharing", "Keluarga"), "platter": ("Sharing", "Keluarga"),
    "gurame": ("Sharing", "Keluarga"), "pizza": ("Sharing", "Keluarga"), "tumpeng": ("Sharing", "Keluarga"),
    "martabak": ("Sharing",), "kiloan": ("Sharing", "Keluarga"),
    "sop": ("Kuah", "Hangat"), "soto": ("Kuah", "Hangat"), "rawon": ("Kuah", "Hangat"), "bakso": ("Kuah", "Hangat"),
    "godog": ("Kuah", "Hangat"), "seblak": ("Kuah", "Hangat"), "ramen": ("Kuah", "Hangat"), "asem": ("Kuah", "Hangat"),
    "capcay": ("Kuah", "Hangat"), "tongseng": ("Kuah", "Hangat"),
    "es": ("Dingin",), "jus": ("Dingin",), "soda": ("Dingin",), "cold": ("Dingin",), "milkshake": ("Dingin",),
    "cola": ("Dingin",), "sprite": ("Dingin",), "iced": ("Dingin",), "mineral": ("Dingin",),
    "kopi": ("Hangat",), "wedang": ("Hangat",), "hot": ("Hangat",), "panas": ("Hangat",), "hangat": ("Hangat",),
    "tarik": ("Hangat",), "tubruk": ("Hangat",), "bandrek": ("Hangat",), "jahe": ("Hangat",),
}


def get_tags(menu_name: str) -> set[str]:
    name = str(menu_name).lower()
    tags: set[str] = set()
    for kw, kw_tags in TAG_KEYWORDS.items():
        if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", name):
            tags.update(kw_tags)
    if "Dingin" in tags:  # "Es Kopi Susu" itu dingin, bukan hangat
        tags.discard("Hangat")
    return tags


def _norm(s: pd.Series) -> pd.Series:
    top = s.max()
    return s / top if top and top > 0 else s * 0.0


def recommend(
    menu: pd.DataFrame,
    history: pd.DataFrame,
    *,
    weather: str,
    group_size: str,
    time_of_day: str,
    customer_id: int | None = None,
    top_n: int = 4,
) -> pd.DataFrame:
    """Kembalikan menu terurut dengan kolom: menu_id, menu_name, category, price, score, reasons.

    `menu`: kolom menu_id, menu_name, category, price, stock. `history`: kolom customer_id, menu_id, qty,
    weather, group_size, time_of_day (satu baris per item transaksi).
    """
    cols = ["menu_id", "menu_name", "category", "price", "score", "reasons"]
    if menu.empty:
        return pd.DataFrame(columns=cols)

    df = menu[menu["stock"] > 0].copy() if "stock" in menu else menu.copy()
    df["tags"] = df["menu_name"].map(get_tags)

    # Aturan keras: sendirian -> bukan menu sharing; hujan -> bukan menu dingin.
    if group_size == "Sendiri":
        df = df[~df["tags"].map(lambda t: "Sharing" in t)]
    if weather == "Hujan":
        df = df[~df["tags"].map(lambda t: "Dingin" in t)]
    if df.empty:
        return pd.DataFrame(columns=cols)

    qty = lambda frame: frame.groupby("menu_id")["qty"].sum().reindex(df["menu_id"]).fillna(0)  # noqa: E731
    if history is None or history.empty:
        zero = pd.Series(0.0, index=df["menu_id"])
        overall = ctx = mine = zero
    else:
        overall = qty(history)
        ctx_mask = (history["weather"] == weather) & (history["group_size"] == group_size) & (history["time_of_day"] == time_of_day)
        ctx = qty(history[ctx_mask])
        mine = qty(history[history["customer_id"] == customer_id]) if customer_id is not None else pd.Series(0.0, index=df["menu_id"])

    df = df.set_index("menu_id")
    df["s_ctx"], df["s_all"], df["s_me"] = _norm(ctx), _norm(overall), _norm(mine)

    def boost(tags: set[str]) -> float:
        b = 0.0
        if group_size == "Keluarga" and ({"Keluarga", "Sharing"} & tags):
            b += 0.6
        if weather == "Hujan" and "Hangat" in tags:
            b += 0.3
        if weather == "Cerah" and "Dingin" in tags:
            b += 0.3
        return b

    df["score"] = 0.35 * df["s_ctx"] + 0.15 * df["s_all"] + 0.30 * df["s_me"] + df["tags"].map(boost)

    def why(row) -> list[str]:
        r: list[str] = []
        if row["s_me"] > 0.3:
            r.append("Favorit pelanggan ini")
        if row["s_ctx"] > 0.5:
            r.append(f"Laris saat {time_of_day.lower()} & {weather.lower()}")
        if group_size == "Keluarga" and ({"Keluarga", "Sharing"} & row["tags"]):
            r.append("Cocok untuk keluarga")
        if weather == "Hujan" and "Hangat" in row["tags"]:
            r.append("Hangat saat hujan")
        if weather == "Cerah" and "Dingin" in row["tags"]:
            r.append("Segar saat cerah")
        if not r and row["s_all"] > 0.5:
            r.append("Populer")
        return r or ["Pilihan menu"]

    df["reasons"] = df.apply(why, axis=1)
    out = df.reset_index().sort_values(["score", "menu_name"], ascending=[False, True]).head(top_n)
    return out[cols].reset_index(drop=True)


def load_history(engine) -> pd.DataFrame:
    from sqlalchemy import text

    with engine.connect() as conn:
        return pd.read_sql(
            text(
                "SELECT t.customer_id, i.menu_id, i.qty, t.weather, t.group_size, t.time_of_day "
                "FROM transaction_items i JOIN transactions t ON t.trx_id = i.trx_id"
            ),
            conn,
        )
