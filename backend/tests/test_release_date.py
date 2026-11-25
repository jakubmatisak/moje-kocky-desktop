"""Dátum vydania setu: Brickset (dátum uvedenia od LEGO), inak BrickEconomy.

Oba prichádzajú v odpovediach, ktoré aj tak ťaháme, volanie navyše nestoja.
Set, na ktorý sa Brickset pýtal ešte pred touto funkciou, sa pri otvorení
detailu opýta raz znova; keď dátum už pozná BrickEconomy, nepýta sa.
"""

from datetime import date

import httpx
import respx
from httpx import AsyncClient

from lego_api.capabilities import Cap
from lego_api.config import Settings
from lego_api.models import BricksetFacts, CatalogItem, CatalogKind, PriceKind
from lego_api.providers.base import CatalogMetadata
from lego_api.providers.brickeconomy import BrickEconomyProvider
from lego_api.providers.brickset import BricksetProvider
from tests.fixtures.brickeconomy import SET_CMF_MEMBER


def _row(**extra) -> dict:
    return {"number": "77000", "numberVariant": 1, "name": "Nový set", "year": 2027, **extra}


def test_brickset_launch_date_is_the_release_date() -> None:
    row = _row(launchDate="2027-03-01T00:00:00Z")
    meta = BricksetProvider(Settings(), "bs-key")._to_metadata(row, "77000-1")
    assert meta.launch_date == date(2027, 3, 1)


def test_without_launch_date_lego_com_first_available_counts() -> None:
    row = _row(LEGOCom={"DE": {"dateFirstAvailable": "2025-06-01T00:00:00Z"}})
    meta = BricksetProvider(Settings(), "bs-key")._to_metadata(row, "77000-1")
    assert meta.launch_date == date(2025, 6, 1)


def test_brickset_without_any_date_has_none() -> None:
    meta = BricksetProvider(Settings(), "bs-key")._to_metadata(_row(), "77000-1")
    assert meta.launch_date is None


async def test_brickeconomy_brings_the_release_date() -> None:
    async with respx.mock(base_url="https://www.brickeconomy.com") as mock:
        mock.get("/api/v1/set/71046-1").mock(return_value=httpx.Response(200, json=SET_CMF_MEMBER))
        data = await BrickEconomyProvider(Settings(), "be-key").get_market(
            "71046-1", PriceKind.SET, cap=Cap.BRICKECONOMY_PRICES
        )
    assert data is not None
    assert data.released_date == date(2024, 5, 1)


async def _catalog(sessionmaker_, **fields) -> None:
    async with sessionmaker_() as session:
        session.add(
            CatalogItem(catalog_num="77000-1", name="Nový set", kind=CatalogKind.SET, **fields)
        )
        await session.commit()


async def test_detail_shows_brickset_date_before_brickeconomy(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _catalog(sessionmaker_, bs_launch_date=date(2027, 3, 1), released_date=date(2027, 2, 1))
    body = (await auth_client.get("/catalog/77000-1")).json()
    assert body["release_date"] == "2027-03-01"


async def test_detail_falls_back_to_brickeconomy_date(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _catalog(sessionmaker_, released_date=date(2027, 2, 1))
    body = (await auth_client.get("/catalog/77000-1")).json()
    assert body["release_date"] == "2027-02-01"


def _fake_brickset(monkeypatch, launch: date | None) -> dict[str, int]:
    calls = {"get_item": 0}

    async def get_item(self, num, *, cap):
        calls["get_item"] += 1
        return CatalogMetadata(catalog_num=num, name="Nový set", launch_date=launch, extended=True)

    monkeypatch.setattr(BricksetProvider, "enabled", property(lambda self: True))
    monkeypatch.setattr(BricksetProvider, "get_item", get_item)
    return calls


async def _asked_before_dates(sessionmaker_, **fields) -> None:
    """Set, na ktorý sa Brickset pýtal pred touto funkciou: plná odpoveď, dátumy nie."""
    from lego_api.models.base import utcnow

    await _catalog(sessionmaker_, **fields)
    async with sessionmaker_() as session:
        facts = await session.get(BricksetFacts, "77000-1")
        if facts is None:
            facts = BricksetFacts(catalog_num="77000-1")
            session.add(facts)
        facts.found = True
        facts.extended_at = utcnow()
        facts.dates_at = None
        await session.commit()


async def test_set_asked_before_dates_asks_brickset_once_on_detail(
    auth_client: AsyncClient, sessionmaker_, monkeypatch
) -> None:
    calls = _fake_brickset(monkeypatch, date(2027, 3, 1))
    await _asked_before_dates(sessionmaker_)

    before = (await auth_client.get("/catalog/77000-1")).json()
    assert before["brickset_dates_pending"] is True

    body = (await auth_client.post("/catalog/77000-1/brickset")).json()
    assert body["release_date"] == "2027-03-01"
    assert body["brickset_dates_pending"] is False

    await auth_client.post("/catalog/77000-1/brickset")
    assert calls["get_item"] == 1


async def test_set_without_launch_date_at_brickset_is_not_asked_again(
    auth_client: AsyncClient, sessionmaker_, monkeypatch
) -> None:
    calls = _fake_brickset(monkeypatch, None)
    await _asked_before_dates(sessionmaker_)

    body = (await auth_client.post("/catalog/77000-1/brickset")).json()
    assert body["release_date"] is None
    assert body["brickset_dates_pending"] is False
    await auth_client.post("/catalog/77000-1/brickset")
    assert calls["get_item"] == 1


async def test_brickeconomy_date_spares_the_brickset_call(
    auth_client: AsyncClient, sessionmaker_, monkeypatch
) -> None:
    calls = _fake_brickset(monkeypatch, date(2027, 3, 1))
    await _asked_before_dates(sessionmaker_, released_date=date(2027, 2, 1))

    body = (await auth_client.post("/catalog/77000-1/brickset")).json()
    assert body["brickset_dates_pending"] is False
    assert calls["get_item"] == 0
