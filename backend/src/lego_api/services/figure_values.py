"""Ceny vo Figúrkach ako v Zbierke: hodnota mojich figúrok a cena chýbajúcich.

Zoznam sérií aj stránka série ukazujú pri každej sérii a figúrke kúpené,
hodnotu, zisk a dátum ceny, rovnako ako karta setu v Zbierke. Ráta sa to
rovnako ako karta Cena mojich figúrok (``series_value``): vlastnené figúrky
zo sérií, duplikáty každý kus, nerozbalený sáčok nie (nemá cenu).

Figúrka, ktorú nemám, má len aktuálnu trhovú cenu, ak ju už poznáme
(obnova cien ju pri zbieranej sérii pýta raz za mesiac). Nič tu nevolá von.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from lego_api.models import ItemStatus, PriceCondition, PriceKind
from lego_api.services.filters import series_num
from lego_api.services.portfolio import (
    ZERO,
    ValuedItem,
    load_items,
    load_snapshots,
    value_items,
)
from lego_api.services.pricing import PriceTarget, resolve_price_target


@dataclass
class FigureValue:
    """Súčty kusov jednej figúrky alebo celej série."""

    pieces: int = 0
    priced: int = 0
    purchase: Decimal = ZERO
    market: Decimal = ZERO
    #: Kúpna cena len kusov s cenou, aby zisk neporovnával nerovnaké.
    priced_purchase: Decimal = ZERO
    #: Niektorá cena je z druhého stavu (≈).
    approx: bool = False
    price_at: datetime | None = None

    def add(self, v: ValuedItem) -> None:
        self.pieces += 1
        self.purchase += v.purchase
        if v.price_source == "missing":
            return
        self.priced += 1
        self.market += v.market_value
        self.priced_purchase += v.purchase
        self.approx = self.approx or v.price_source == "market_approx"
        if v.price_at is not None and (self.price_at is None or v.price_at > self.price_at):
            self.price_at = v.price_at

    def merge(self, other: FigureValue) -> None:
        self.pieces += other.pieces
        self.priced += other.priced
        self.purchase += other.purchase
        self.market += other.market
        self.priced_purchase += other.priced_purchase
        self.approx = self.approx or other.approx
        if other.price_at is not None and (self.price_at is None or other.price_at > self.price_at):
            self.price_at = other.price_at

    @property
    def market_total(self) -> Decimal | None:
        """Bez jedinej ceny None, nie nula (rozhranie ukáže pomlčku)."""
        return self.market if self.priced else None

    @property
    def profit(self) -> Decimal | None:
        return self.market - self.priced_purchase if self.priced else None

    @property
    def profit_pct(self) -> float | None:
        profit = self.profit
        if profit is None or self.priced_purchase <= 0:
            return None
        return float(profit / self.priced_purchase * 100)

    @property
    def price_missing(self) -> int:
        return self.pieces - self.priced


async def my_figure_values(session: AsyncSession, user_id: int) -> dict[str, FigureValue]:
    """Vlastnené figúrky zo sérií podľa katalógového čísla (sáčky bez figúrky nie)."""
    mine = [
        item
        for item in await load_items(session, user_id)
        if item.status == ItemStatus.OWNED
        and not item.unidentified
        and item.catalog is not None
        and series_num(item.catalog, False) is not None
    ]
    if not mine:
        return {}
    index = await load_snapshots(
        session, {resolve_price_target(i, i.catalog).catalog_num for i in mine}
    )
    out: dict[str, FigureValue] = {}
    for valued in value_items(mine, index):
        out.setdefault(valued.item.catalog_num, FigureValue()).add(valued)
    return out


async def market_now(
    session: AsyncSession, nums: Iterable[str]
) -> dict[str, tuple[Decimal, datetime | None]]:
    """Posledná známa cena nového kusu figúrky, ktorú nemám (cení sa ako set)."""
    wanted = set(nums)
    if not wanted:
        return {}
    index = await load_snapshots(session, wanted)
    out: dict[str, tuple[Decimal, datetime | None]] = {}
    for num in wanted:
        target = PriceTarget(num, PriceKind.SET, PriceCondition.NEW)
        price = index.value_at(target)
        if price is not None:
            out[num] = (price, index.latest_time(target))
    return out
