"""Cena celej série a chýbajúcich figúrok: na posúdenie ponuky na kúpu.

Karta série vo Figúrkach ukáže popri mojich figúrkach aj súčet cien tých,
ktoré mi chýbajú, a celej série (každá figúrka raz, cena nového kusu), aj
keď zo série nemám nič. Ceny chýbajúcich sa ťahajú len na kliknutie
(``refresh-all?num=…&whole_series=true``) a cena mladšia než
``price_max_age_hours`` (15 dní) sa berie ako aktuálna.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from lego_api.config import Settings
from lego_api.models import (
    CatalogItem,
    CatalogKind,
    CollectionItem,
    ItemCondition,
    PriceCondition,
    PriceKind,
    PriceSnapshot,
    User,
)
from lego_api.services.refresh import collect_targets, refresh_prices, reset_state

DAY1 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
DAY2 = DAY1 + timedelta(days=1)
DAY3 = DAY1 + timedelta(days=2)


def _snap(
    num: str, price: str, when: datetime, condition: PriceCondition = PriceCondition.NEW
) -> PriceSnapshot:
    return PriceSnapshot(
        catalog_num=num,
        source="brickeconomy",
        price_kind=PriceKind.SET,
        condition=condition,
        avg_price=Decimal(price),
        captured_at=when,
    )


def _catalog(session) -> None:
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


async def _seed(sessionmaker_, *, third_price: bool = True) -> None:
    async with sessionmaker_() as session:
        _catalog(session)
        session.add(_snap("42233-1", "5", DAY1))
        session.add(_snap("42233-1", "6", DAY3))
        session.add(_snap("42233-2", "4.5", DAY2))
        if third_price:
            session.add(_snap("42233-3", "9", DAY1))
        await session.commit()


async def _own(auth_client: AsyncClient, *nums: str) -> None:
    for num in nums:
        response = await auth_client.post(
            "/items",
            json={"catalog_num": num, "condition": "new_sealed", "purchase_price_eur": "3"},
        )
        assert response.status_code == 201, response.text


async def test_missing_figures_and_the_whole_series_are_summed(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client, "42233-1", "42233-2")

    body = (await auth_client.get("/prices/series/42233")).json()

    assert (body["member_count"], body["missing_count"], body["missing_priced"]) == (3, 1, 1)
    assert body["missing_total"] == "9.00"
    assert (body["series_total"], body["series_priced"]) == ("19.50", 3)
    # Moje figúrky ostávajú, ako boli.
    assert body["market_total"] == "10.50"


async def test_series_i_have_nothing_from_has_the_whole_price(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)

    body = (await auth_client.get("/prices/series/42233")).json()

    assert body["owned_count"] == 0
    assert body["market_total"] is None
    assert (body["missing_count"], body["missing_total"]) == (3, "19.50")
    assert body["series_total"] == "19.50"


async def test_whole_series_counts_each_figure_once(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_)
    await _own(auth_client, "42233-1", "42233-1")

    body = (await auth_client.get("/prices/series/42233")).json()

    assert body["market_total"] == "12.00"
    assert body["series_total"] == "19.50"
    assert body["missing_count"] == 2


async def test_whole_series_uses_only_the_new_price(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Ponúkajú sa nové figúrky; cena rozbaleného kusu by súčet skreslila."""
    await _seed(sessionmaker_, third_price=False)
    async with sessionmaker_() as session:
        session.add(_snap("42233-3", "2", DAY1, PriceCondition.USED))
        await session.commit()

    body = (await auth_client.get("/prices/series/42233")).json()

    assert (body["series_total"], body["series_priced"]) == ("10.50", 2)
    assert (body["missing_total"], body["missing_priced"]) == ("10.50", 2)
    assert body["history_all"] == []


async def test_whole_series_line_is_the_sum_of_every_figure(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Pred prvou cenou figúrky sa ráta jej prvá cena, ako v čiare mojich figúrok."""
    await _seed(sessionmaker_)

    body = (await auth_client.get("/prices/series/42233")).json()

    points = [(p["captured_at"][:10], p["avg_price"]) for p in body["history_all"]]
    assert points == [
        ("2026-09-01", "18.50"),
        ("2026-09-02", "18.50"),
        ("2026-09-03", "19.50"),
    ]


async def test_whole_series_line_waits_for_every_figure(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(sessionmaker_, third_price=False)

    body = (await auth_client.get("/prices/series/42233")).json()

    assert body["history_all"] == []
    assert (body["series_priced"], body["member_count"]) == (2, 3)


# --- obnova celej série na kliknutie ---------------------------------------------


def _settings() -> Settings:
    return Settings(brickeconomy_key="be-key", price_max_age_hours=360, price_refresh_budget=60)


async def _plan_seed(session, *, owned: tuple[str, ...] = ()) -> None:
    session.add(User(id=1, email="u1@x.sk", password_hash="x"))
    _catalog(session)
    for num in owned:
        session.add(
            CollectionItem(
                user_id=1,
                catalog_num=num,
                condition=ItemCondition.NEW_SEALED,
                flags=[],
                purchase_price_eur=Decimal("3"),
            )
        )
    now = datetime.now(UTC)
    # Cena mladšia než 15 dní je aktuálna, staršia sa obnoví.
    session.add(_snap("42233-1", "5", now - timedelta(days=3)))
    session.add(_snap("42233-2", "5", now - timedelta(days=20)))
    await session.commit()


async def test_whole_series_plan_asks_for_every_figure_older_than_fifteen_days(session) -> None:
    reset_state()
    await _plan_seed(session)

    plan = await collect_targets(session, 1, _settings(), only="42233", whole_series=True)

    assert sorted(t.catalog_num for t in plan.targets) == ["42233-2", "42233-3"]
    assert {(t.price_kind, t.condition) for t in plan.targets} == {
        (PriceKind.SET, PriceCondition.NEW)
    }
    assert plan.skipped_fresh == 1


async def test_whole_series_plan_includes_my_figures_once(session) -> None:
    reset_state()
    await _plan_seed(session, owned=("42233-2",))

    plan = await collect_targets(session, 1, _settings(), only="42233", whole_series=True)

    assert sorted(t.catalog_num for t in plan.targets) == ["42233-2", "42233-3"]


async def test_series_refresh_without_whole_series_asks_only_for_my_figures(session) -> None:
    reset_state()
    await _plan_seed(session, owned=("42233-2",))

    plan = await collect_targets(session, 1, _settings(), only="42233")

    assert [t.catalog_num for t in plan.targets] == ["42233-2"]


async def test_refresh_plan_endpoint_says_how_many_calls_it_costs(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    async with sessionmaker_() as session:
        _catalog(session)
        session.add(_snap("42233-1", "5", datetime.now(UTC) - timedelta(hours=2)))
        await session.commit()

    response = await auth_client.get("/prices/series/42233/refresh-plan")

    assert response.status_code == 200, response.text
    assert response.json() == {"calls": 2, "fresh": 1, "max_age_days": 1}


async def test_whole_series_refresh_asks_only_for_figures_without_a_current_price(
    session, sessionmaker_
) -> None:
    from tests.test_refresh import FakeProvider

    reset_state()
    await _plan_seed(session)
    provider = FakeProvider()
    settings = _settings()
    settings.price_refresh_delay_seconds = 0.0

    await refresh_prices(sessionmaker_, 1, settings, provider, only="42233", whole_series=True)

    assert sorted(num for num, _ in provider.calls) == ["42233-2", "42233-3"]


# --- zoznam sérií -------------------------------------------------------------------


async def test_series_list_shows_the_whole_series_price_when_known(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Zoznam nič nesťahuje, len sčíta ceny, ktoré už sú v databáze."""
    await _seed(sessionmaker_, third_price=False)

    rows = (await auth_client.get("/minifigs/series")).json()["series"]
    row = next(r for r in rows if r["series_num"] == "42233")

    assert (row["series_total"], row["series_priced"]) == ("10.50", 2)


async def test_series_list_without_any_price_has_no_whole_price(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    async with sessionmaker_() as session:
        _catalog(session)
        await session.commit()

    rows = (await auth_client.get("/minifigs/series")).json()["series"]
    row = next(r for r in rows if r["series_num"] == "42233")

    assert (row["series_total"], row["series_priced"]) == (None, 0)
