"""Hodnota mojich figúrok jednej série: súčty a graf ako pri jednej figúrke.

BrickEconomy cenu celej série nemá (pod holým číslom vráti prvú figúrku),
preto je hodnota série súčet mojich vlastnených figúrok. Nerozbalený sáčok
do nej nepatrí: nie je to figúrka a trhovú cenu pod holým číslom nemá.

Duplikáty (dva kusy tej istej figúrky) sa bežne rátajú oba. S ``single``
sa ráta každá figúrka raz (prvý kúpený kus), teda hodnota jednej série;
rozhranie to ponúka, len keď je séria kompletná.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from lego_api.models import CatalogItem, CollectionItem, ItemStatus
from lego_api.services.filters import series_num
from lego_api.services.portfolio import (
    ZERO,
    load_items,
    load_snapshots,
    value_items,
)
from lego_api.services.pricing import resolve_price_target


@dataclass
class SeriesValue:
    owned_count: int = 0
    #: Rôzne figúrky série, ktoré mám.
    distinct_count: int = 0
    #: Koľko figúrok séria má (``series_size``); bez údaja None.
    series_size: int | None = None
    #: Figúrky s trhovou alebo ručnou cenou.
    priced_count: int = 0
    purchase_total: Decimal = ZERO
    #: Súčet cien figúrok s cenou; bez jedinej ceny None (nie nula).
    market_total: Decimal | None = None
    #: Kúpna cena len figúrok s cenou, aby zisk neporovnával nerovnaké.
    priced_purchase: Decimal = ZERO
    #: Niektorá cena je z druhého stavu (≈).
    approx: bool = False
    price_at: datetime | None = None

    @property
    def duplicates(self) -> int:
        """Kusy navyše oproti jednému kusu každej figúrky."""
        return self.owned_count - self.distinct_count

    @property
    def complete(self) -> bool:
        return bool(self.series_size) and self.distinct_count >= (self.series_size or 0)


def _mine(items: list[CollectionItem], num: str) -> list[CollectionItem]:
    return [
        i
        for i in items
        if i.status == ItemStatus.OWNED
        and not i.unidentified
        and i.catalog is not None
        and series_num(i.catalog, False) == num
    ]


def _first_of_each(items: list[CollectionItem]) -> list[CollectionItem]:
    """Jeden kus na figúrku: prvý kúpený (bez dátumu nakoniec), potom prvý pridaný."""
    chosen: dict[str, CollectionItem] = {}
    for item in sorted(items, key=lambda i: (i.purchase_date is None, i.purchase_date, i.id)):
        chosen.setdefault(item.catalog_num, item)
    return list(chosen.values())


async def series_value(
    session: AsyncSession, user_id: int, num: str, *, single: bool = False
) -> SeriesValue:
    series = await session.get(CatalogItem, num)
    size = series.series_size if series is not None else None
    items = _mine(await load_items(session, user_id), num)
    if not items:
        return SeriesValue(series_size=size)
    distinct = len({i.catalog_num for i in items})
    owned_count = len(items)
    if single:
        items = _first_of_each(items)
    nums = {resolve_price_target(i, i.catalog).catalog_num for i in items}
    index = await load_snapshots(session, nums)
    valued = value_items(items, index)

    priced = [v for v in valued if v.price_source != "missing"]
    times = [v.price_at for v in priced if v.price_at is not None]
    return SeriesValue(
        owned_count=owned_count,
        distinct_count=distinct,
        series_size=size,
        priced_count=len(priced),
        purchase_total=sum((v.purchase for v in valued), ZERO),
        market_total=sum((v.market_value for v in priced), ZERO) if priced else None,
        priced_purchase=sum((v.purchase for v in priced), ZERO),
        approx=any(v.price_source == "market_approx" for v in priced),
        price_at=max(times) if times else None,
    )
