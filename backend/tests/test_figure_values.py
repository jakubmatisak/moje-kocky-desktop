"""Ceny vo Figúrkach ako v Zbierke: pri sérii aj pri každej figúrke.

Séria: súčet mojich figúrok (duplikáty sa rátajú, ako karta Cena mojich
figúrok). Figúrka, ktorú mám: kúpené, hodnota, zisk a dátum ceny.
Figúrka, ktorú nemám: len aktuálna trhová cena s dátumom, ak ju poznáme.
"""

from httpx import AsyncClient

from tests.test_series_value import _own, _seed


async def test_series_row_has_my_value_profit_and_price_date(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client)

    rows = (await auth_client.get("/minifigs/series")).json()["series"]
    row = next(r for r in rows if r["series_num"] == "42233")

    assert row["purchase_total"] == "7.00"
    assert row["market_total"] == "10.50"
    assert row["profit"] == "3.50"
    assert row["profit_pct"] == 50.0
    assert row["price_at"].startswith("2026-09-03")
    assert row["price_missing"] == 0


async def test_series_without_my_figures_has_no_sums(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Séria, z ktorej nemám nič: žiadne sumy, nie nuly."""
    await _seed(sessionmaker_)

    rows = (await auth_client.get("/minifigs/series")).json()["series"]
    row = next(r for r in rows if r["series_num"] == "42233")

    assert row["purchase_total"] is None
    assert row["market_total"] is None
    assert row["profit"] is None


async def test_members_show_my_value_and_the_market_price_of_missing_ones(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client)
    # Duplikát prvej figúrky: v súčte sa ráta aj on.
    await auth_client.post(
        "/items",
        json={"catalog_num": "42233-1", "condition": "new_sealed", "purchase_price_eur": "5"},
    )

    body = (await auth_client.get("/minifigs/series/42233")).json()
    members = {m["catalog"]["catalog_num"]: m for m in body["members"]}

    first = members["42233-1"]
    assert (first["owned"], first["purchase_total"], first["market_total"]) == (2, "8.00", "12.00")
    assert (first["profit"], first["profit_pct"]) == ("4.00", 50.0)
    assert first["price_at"].startswith("2026-09-03")
    assert first["market_now"] is None

    missing = members["42233-3"]
    assert missing["owned"] == 0
    assert missing["purchase_total"] is None
    assert missing["market_now"] == "9.00"
    assert missing["market_now_at"].startswith("2026-09-01")

    series = body["series"]
    assert (series["purchase_total"], series["market_total"], series["duplicates"]) == (
        "12.00",
        "16.50",
        1,
    )
