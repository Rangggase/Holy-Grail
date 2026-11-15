from datetime import date, datetime

from holygrail.services import reports as r
from holygrail.services.checkout import checkout
from tests.conftest import menu_id


def _buy(engine, name, lines, when, key, method="QRIS"):
    return checkout(engine, lines=lines, customer_name=name, payment_method=method, paid=0, weather="Cerah",
                    group_size="Sendiri", cashier_id=None, idempotency_key=key, now=when)


def test_kpis_segments_and_ranges(engine):
    nasi, teh, paket = (menu_id(engine, n) for n in ("Nasi Goreng Spesial", "Es Teh Manis", "Paket Hemat Ber-4"))
    _buy(engine, "Budi", [(nasi, 2), (teh, 1)], datetime(2026, 3, 1, 12, 30), "a")   # 57.000
    _buy(engine, "Budi", [(nasi, 1)], datetime(2026, 3, 2, 19, 5), "b")             # 25.000
    _buy(engine, "Siti", [(paket, 3)], datetime(2026, 3, 2, 20, 0), "c")            # 300.000
    lines = r.sales_lines(engine, date(2026, 3, 1), date(2026, 3, 2))
    k = r.kpis(lines)
    assert (k.revenue, k.transactions, k.items_sold) == (382_000, 3, 7)
    assert k.avg_basket == 382_000 // 3 and k.best_seller == "Nasi Goreng Spesial"

    seg = r.customer_segments(lines).set_index("nama")
    assert seg.loc["Budi", "total_belanja"] == 82_000 and seg.loc["Budi", "jumlah_transaksi"] == 2
    assert set(seg.segmen) == {"Bronze"}

    assert list(r.daily_sales(lines).transaksi) == [1, 2]
    hourly = r.hourly_sales(lines).set_index("jam")
    assert hourly.loc[12, "omzet"] == 57_000 and hourly.loc[3, "omzet"] == 0 and len(hourly) == 24
    assert list(r.top_menu(lines, drinks=True).menu) == ["Es Teh Manis"]

    # rentang tanggal inklusif; hari tanpa data kosong
    assert r.kpis(r.sales_lines(engine, date(2026, 3, 1), date(2026, 3, 1))).revenue == 57_000
    empty = r.sales_lines(engine, date(2025, 1, 1), date(2025, 1, 2))
    assert r.kpis(empty).revenue == 0 and r.transaction_table(empty).empty and r.customer_segments(empty).empty
    assert len(r.transaction_table(lines)) == 4


def test_segment_thresholds():
    assert [r.segment_for(v) for v in (0, 999_999, 1_000_000, 3_000_000, 4_500_000, 10_000_000)] == [
        "Bronze", "Bronze", "Silver", "Gold", "Platinum", "Diamond"]


def test_csv_export_neutralizes_formula_injection():
    import pandas as pd

    df = pd.DataFrame({"Pelanggan": ["=HYPERLINK(\"http://x\")", "+cmd", "-1+1", "@SUM(A1)", "Budi"], "Jumlah": [1, 2, 3, 4, 5]})
    text = r.to_safe_csv(df).decode("utf-8-sig")
    lines = text.splitlines()[1:]
    assert all(l.startswith("'") or l.startswith('"\'') or l.startswith("Budi") for l in (x for x in lines))
    assert "'=HYPERLINK" in text and "'+cmd" in text and "'-1+1" in text and "'@SUM" in text
