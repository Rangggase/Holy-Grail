import pandas as pd

from holygrail.services.recommender import get_tags, recommend

MENU = pd.DataFrame(
    [
        (1, "Soto Betawi", "Makanan Berat", 45000, 10),
        (2, "Es Teh Manis", "Minuman", 7000, 10),
        (3, "Paket Hemat Ber-4", "Paket Jumbo", 100000, 10),
        (4, "Teh Tarik Hangat", "Minuman", 15000, 10),
        (5, "Nasi Goreng Spesial", "Makanan Berat", 25000, 0),
    ],
    columns=["menu_id", "menu_name", "category", "price", "stock"],
)
EMPTY = pd.DataFrame(columns=["customer_id", "menu_id", "qty", "weather", "group_size", "time_of_day"])


def test_tags_whole_word_and_cold_overrides_hot():
    assert "Dingin" in get_tags("Es Teh Manis Jumbo")
    assert get_tags("Es Kopi Susu Gula Aren") == {"Dingin"}
    assert "Dingin" not in get_tags("Mie Godog Jawa")
    assert {"Kuah", "Hangat"} <= get_tags("Soto Betawi")


def test_rain_removes_cold_and_boosts_warm():
    out = recommend(MENU, EMPTY, weather="Hujan", group_size="Keluarga", time_of_day="Siang", top_n=10)
    assert "Es Teh Manis" not in set(out.menu_name)
    assert "Teh Tarik Hangat" in set(out.menu_name)


def test_alone_removes_sharing_and_out_of_stock_excluded():
    out = recommend(MENU, EMPTY, weather="Cerah", group_size="Sendiri", time_of_day="Siang", top_n=10)
    names = set(out.menu_name)
    assert "Paket Hemat Ber-4" not in names and "Nasi Goreng Spesial" not in names


def test_family_prefers_sharing():
    out = recommend(MENU, EMPTY, weather="Cerah", group_size="Keluarga", time_of_day="Siang")
    assert out.iloc[0].menu_name == "Paket Hemat Ber-4"
    assert "Cocok untuk keluarga" in out.iloc[0].reasons


def test_personal_history_lifts_item():
    hist = pd.DataFrame([dict(customer_id=7, menu_id=1, qty=9, weather="Cerah", group_size="Sendiri", time_of_day="Malam")])
    out = recommend(MENU, hist, weather="Cerah", group_size="Sendiri", time_of_day="Siang", customer_id=7)
    assert out.iloc[0].menu_name == "Soto Betawi"
    assert "Favorit pelanggan ini" in out.iloc[0].reasons


def test_deterministic_and_empty_menu():
    a = recommend(MENU, EMPTY, weather="Cerah", group_size="Sendiri", time_of_day="Pagi")
    b = recommend(MENU, EMPTY, weather="Cerah", group_size="Sendiri", time_of_day="Pagi")
    assert a.equals(b)
    assert recommend(MENU.iloc[0:0], EMPTY, weather="Cerah", group_size="Sendiri", time_of_day="Pagi").empty
