"""Generator data demo yang deterministik (seed tetap) — nama pelanggan fiktif, bukan data pribadi nyata."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine

from holygrail import db
from holygrail.services.checkout import time_of_day
from holygrail.services.recommender import get_tags

FIRST = ["Budi", "Siti", "Agus", "Dewi", "Rina", "Eko", "Wulan", "Hendra", "Putri", "Dimas", "Ayu", "Fajar", "Lestari", "Rizky",
         "Maya", "Bayu", "Nadia", "Andi", "Sari", "Yoga", "Intan", "Reza", "Citra", "Galih", "Tiara", "Arif", "Laras", "Hadi"]
LAST = ["Santoso", "Wijaya", "Pratama", "Lestari", "Hidayat", "Saputra", "Nugroho", "Kusuma", "Permata", "Rahman", "Utami",
        "Firmansyah", "Setiawan", "Maulana", "Anggraini", "Purnama", "Wibowo", "Halim", "Cahyono", "Susanto"]


def seed_demo(engine: Engine, *, n_customers: int = 420, n_transactions: int = 6000, end: date | None = None, seed: int = 42) -> dict:
    rng = random.Random(seed)
    end = end or date.today()
    with engine.begin() as conn:
        menu_rows = conn.execute(select(db.menu.c.menu_id, db.menu.c.menu_name, db.menu.c.category, db.menu.c.price)).all()
        cashier_ids = [r[0] for r in conn.execute(select(db.staff.c.staff_id).where(db.staff.c.role == "kasir"))] or [None]

        names: set[str] = set()
        while len(names) < n_customers:
            names.add(f"{rng.choice(FIRST)} {rng.choice(LAST)}")
        names_list = sorted(names)
        rng.shuffle(names_list)
        conn.execute(insert(db.customers), [dict(name=n, name_key=n.lower(), created_at=datetime.combine(end - timedelta(days=365), datetime.min.time())) for n in names_list])
        cust_ids = [r[0] for r in conn.execute(select(db.customers.c.customer_id).order_by(db.customers.c.customer_id))]
        # Bobot kunjungan: sedikit pelanggan sangat loyal (distribusi miring).
        weights = [min(rng.paretovariate(2.0), 8.0) for _ in cust_ids]
        favorites = {c: rng.sample(menu_rows, 4) for c in cust_ids}

        foods = [m for m in menu_rows if m.category != "Minuman"]
        drinks = [m for m in menu_rows if m.category == "Minuman"]
        sharing = [m for m in menu_rows if "Sharing" in get_tags(m.menu_name)]
        solo_foods = [m for m in foods if m not in sharing]
        payments = ["Tunai"] * 5 + ["QRIS"] * 4 + ["Debit/Kredit"]

        start_dt = datetime.combine(end - timedelta(days=364), datetime.min.time())
        sold: dict[int, int] = {}
        movement_rows: list[dict] = []
        trx_id = 0
        for n in range(n_transactions):
            cust = rng.choices(cust_ids, weights)[0]
            day = start_dt + timedelta(days=rng.random() ** 0.8 * 364.99)  # sedikit lebih ramai belakangan ini
            hour = rng.choices(range(8, 23), [2, 3, 5, 9, 10, 8, 4, 3, 5, 8, 9, 7, 4, 2, 1])[0]
            when = day.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
            if when > datetime.now():
                when -= timedelta(days=1)
            weather = rng.choices(["Cerah", "Hujan"], [58, 42])[0]
            group = rng.choices(["Sendiri", "Keluarga"], [45, 55])[0]
            picks: dict[int, tuple] = {}
            if group == "Keluarga":
                for m in rng.sample(sharing, k=rng.randint(1, 2)) + rng.sample(foods, k=rng.randint(1, 3)) + rng.sample(drinks, k=rng.randint(2, 4)):
                    picks[m.menu_id] = (m, rng.randint(1, 2))
            else:
                pool = favorites[cust] if rng.random() < 0.45 else solo_foods
                picks_m = [rng.choice(pool)] + ([rng.choice(drinks)] if rng.random() < 0.85 else []) + ([rng.choice(solo_foods)] if rng.random() < 0.3 else [])
                for m in picks_m:
                    picks[m.menu_id] = (m, 1)
            total = sum(m.price * q for m, q in picks.values())
            method = rng.choice(payments)
            paid = total if method != "Tunai" else ((total // 5000) + 1) * 5000 if rng.random() < 0.7 else total
            trx_id += 1
            conn.execute(insert(db.transactions).values(
                trx_id=trx_id, idempotency_key=f"demo-{seed}-{n}", customer_id=cust, cashier_id=rng.choice(cashier_ids),
                created_at=when, weather=weather, group_size=group, time_of_day=time_of_day(when.hour),
                payment_method=method, total=total, paid=paid, change_amount=paid - total,
            ))
            conn.execute(insert(db.transaction_items), [
                dict(trx_id=trx_id, menu_id=m.menu_id, qty=q, unit_price=m.price, subtotal=m.price * q) for m, q in picks.values()
            ])
            for m, q in picks.values():
                sold[m.menu_id] = sold.get(m.menu_id, 0) + q
                movement_rows.append(dict(menu_id=m.menu_id, delta=-q, reason="sale", trx_id=trx_id, created_at=when))

        # Stok akhir realistis: sebagian kecil menu sengaja tipis agar fitur "stok menipis" terlihat.
        for i, m in enumerate(menu_rows):
            final = rng.randint(2, 9) if i % 11 == 0 else rng.randint(25, 120)
            initial = final + sold.get(m.menu_id, 0)
            conn.execute(update(db.menu).where(db.menu.c.menu_id == m.menu_id).values(stock=final))
            conn.execute(insert(db.stock_movements).values(
                menu_id=m.menu_id, delta=initial, reason="initial", created_at=start_dt - timedelta(days=1)))
        conn.execute(insert(db.stock_movements), movement_rows)
    return {"customers": len(cust_ids), "transactions": trx_id}
