"""Hodnota mojich figúrok zo série: súčty, graf a obnova len vlastných figúrok.

BrickEconomy cenu celej série nemá: pod holým číslom (42233) vráti prvú
figúrku (42233-1). Nerozbalený sáčok sa preto pod holým číslom necení.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from lego_api.models import (
    CatalogItem,
    CatalogKind,
    PriceCondition,
    PriceKind,
    PriceSnapshot,
)
from lego_api.services.pricing import PriceTarget, source_prices

DAY1 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
DAY2 = DAY1 + timedelta(days=1)
DAY3 = DAY1 + timedelta(days=2)


def _snap(num: str, price: str, when: datetime) -> PriceSnapshot:
    return PriceSnapshot(
        catalog_num=num,
        source="brickeconomy",
        price_kind=PriceKind.SET,
        condition=PriceCondition.NEW,
        avg_price=Decimal(price),
        captured_at=when,
    )


async def _seed(sessionmaker_) -> None:
    async with sessionmaker_() as session:
        session.add(
            CatalogItem(
                catalog_num="42233", name="Mighty Machines", kind=CatalogKind.SET, series_size=3
            )
        )
        for i in range(1, 4):
            session.add(
                CatalogItem(
                    catalog_num=f"42233-{i}",
                    name=f"Stroj {i}",
                    kind=CatalogKind.SET,
                    parent_num="42233",
                )
            )
        session.add(_snap("42233-1", "5", DAY1))
        session.add(_snap("42233-1", "6", DAY3))
        session.add(_snap("42233-2", "4.5", DAY2))
        # Chýbajúca figúrka má cenu, do mojej hodnoty nepatrí.
        session.add(_snap("42233-3", "9", DAY1))
        await session.commit()


async def _own(auth_client: AsyncClient) -> None:
    for num, price in (("42233-1", "3"), ("42233-2", "4")):
        response = await auth_client.post(
            "/items",
            json={"catalog_num": num, "condition": "new_sealed", "purchase_price_eur": price},
        )
        assert response.status_code == 201, response.text
    # Nerozbalený sáčok pod holým číslom série.
    response = await auth_client.post("/items", json={"catalog_num": "42233"})
    assert response.status_code == 201, response.text


async def test_series_value_sums_my_figures_only(auth_client: AsyncClient, sessionmaker_) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client)

    response = await auth_client.get("/prices/series/42233")
    assert response.status_code == 200, response.text
    body = response.json()

    assert (body["owned_count"], body["priced_count"]) == (2, 2)
    assert body["purchase_total"] == "7.00"
    assert body["market_total"] == "10.50"
    assert body["profit"] == "3.50"
    assert body["approx"] is False


async def test_series_value_without_my_figures_is_empty(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)

    body = (await auth_client.get("/prices/series/42233")).json()

    assert (body["owned_count"], body["priced_count"]) == (0, 0)
    assert body["market_total"] is None


async def test_sealed_bag_is_not_priced_under_the_bare_series_number() -> None:
    series = CatalogItem(
        catalog_num="42233", name="Mighty Machines", kind=CatalogKind.SET, series_size=8
    )
    target = PriceTarget("42233", PriceKind.SET, PriceCondition.NEW)

    assert source_prices(target, series) is False


async def test_duplicates_count_and_single_series_value_when_complete(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client)
    # Druhý kus prvej figúrky (duplikát) a tretia figúrka: séria je kompletná.
    for num, price in (("42233-1", "2"), ("42233-3", "8")):
        response = await auth_client.post(
            "/items",
            json={"catalog_num": num, "condition": "new_sealed", "purchase_price_eur": price},
        )
        assert response.status_code == 201, response.text

    every = (await auth_client.get("/prices/series/42233")).json()
    assert (every["owned_count"], every["distinct_count"], every["duplicates"]) == (4, 3, 1)
    assert every["complete"] is True
    assert every["single"] is False
    # Duplikát sa pripočíta: 6 + 6 + 4,5 + 9.
    assert every["market_total"] == "25.50"

    one = (await auth_client.get("/prices/series/42233", params={"single": "true"})).json()
    assert one["single"] is True
    assert one["market_total"] == "19.50"
    assert one["purchase_total"] == "15.00"


async def test_single_value_is_ignored_for_an_incomplete_series(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client)

    body = (await auth_client.get("/prices/series/42233", params={"single": "true"})).json()

    assert (body["complete"], body["single"]) == (False, False)
    assert body["market_total"] == "10.50"
