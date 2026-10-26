"""Hodnota mojich figúrok jednej série: súčty a graf ako pri jednej figúrke.

BrickEconomy cenu celej série nemá (pod holým číslom vráti prvú figúrku),
preto je hodnota série súčet mojich vlastnených figúrok. Nerozbalený sáčok
do nej nepatrí: nie je to figúrka a trhovú cenu pod holým číslom nemá.

Graf je súčet histórie cien z BrickEconomy, ako pri jednej figúrke, nie od
nákupu. Pred prvou cenou figúrky sa ráta jej prvá cena (odhad), aby súčet
nerástol len tým, ako pribúdajú ceny; ``estimated_until`` povie, odkedy je
súčet zo skutočných cien. Nákupy a predaje sú udalosti na zvislé čiary.

Čiary sú dve, ako v grafe setu: Nový (cena nového kusu, figúrka bez nej
spadne na rozbalenú, ≈) a Rozbalený. Rozbalená je len vtedy, keď ju pozná
každá figúrka: súčet bez jednej by bol nízky a vyzeral by ako pád ceny.

Duplikáty (dva kusy tej istej figúrky) sa bežne rátajú oba. S ``single``
sa ráta každá figúrka raz (prvý kúpený kus), teda hodnota jednej série;
rozhranie to ponúka, len keď je séria kompletná.

Na posúdenie ponuky na kúpu karta ukáže aj súčet cien figúrok, ktoré mi
chýbajú, a celej série (každá figúrka raz), aj keď zo série nemám nič.
Ponúkajú sa nové figúrky, preto len cena nového kusu pod číslom figúrky
(ako ``figure_values.market_now``), bez náhrady rozbalenou. Čiara celej
série (``history_all``) je súčet figúrok, ktoré cenu majú (11 z 12 má
graf tiež); figúrka bez ceny v nej chýba celý čas, takže súčet neklesne
ani neposkočí, a ``series_priced`` povie, koľko ich je. Ceny
chýbajúcich sa ťahajú len na kliknutie (``refresh.collect_targets``
s ``whole_series``); tu sa nič nevolá.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lego_api import visibility
from lego_api.models import (
    CatalogItem,
    CollectionItem,
    ItemStatus,
    PriceCondition,
    PriceKind,
)
from lego_api.services.filters import series_num
from lego_api.services.portfolio import (
    ZERO,
    SnapshotIndex,
    ValuedItem,
    load_items,
    load_snapshots,
    value_items,
)
from lego_api.services.pricing import PriceTarget, resolve_price_target


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
    #: (deň, súčet cien) od najstaršej ceny; pred prvou cenou figúrky jej prvá cena.
    history: list[tuple[datetime, Decimal]] = field(default_factory=list)
    #: To isté z cien rozbalených kusov; prázdne, keď ju niektorá figúrka nemá.
    history_used: list[tuple[datetime, Decimal]] = field(default_factory=list)
    #: Prvý deň, keď je súčet celý zo skutočných cien; bez odhadu None.
    estimated_until: date | None = None
    #: Nákupy a predaje figúrok série po dňoch (deň, druh, počet, suma).
    events: list[tuple[date, str, int, Decimal]] = field(default_factory=list)
    #: Figúrky série v katalógu (bez kľúča Rebrickable žiadne).
    member_count: int = 0
    #: Figúrky, ktoré nemám, a koľko z nich má cenu nového kusu.
    missing_count: int = 0
    missing_priced: int = 0
    missing_total: Decimal | None = None
    #: Celá séria, každá figúrka raz, cena nového kusu; bez jedinej ceny None.
    series_priced: int = 0
    series_total: Decimal | None = None
    #: Súčet histórie cien figúrok s cenou nového kusu (koľko: ``series_priced``).
    history_all: list[tuple[datetime, Decimal]] = field(default_factory=list)

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


def _history(
    market: list[ValuedItem],
    manual: Decimal,
    index: SnapshotIndex,
    condition: PriceCondition = PriceCondition.NEW,
) -> tuple[list[tuple[datetime, Decimal]], date | None]:
    """Súčet cien po dňoch od najstaršej snímky; odhad do prvej ceny každej figúrky.

    Nový berie aj druhý stav (≈), keď figúrka cenu nového kusu nemá. Rozbalený
    len presný stav, a keď ho niektorá figúrka nemá vôbec, čiara nie je.
    """
    targets = [
        replace(resolve_price_target(v.item, v.catalog), condition=condition) for v in market
    ]
    return _sum_history(targets, manual, index, exact=condition == PriceCondition.USED)


def _sum_history(
    targets: list[PriceTarget], manual: Decimal, index: SnapshotIndex, *, exact: bool
) -> tuple[list[tuple[datetime, Decimal]], date | None]:
    """Jadro ``_history``: s ``exact`` len presný stav a bez ceny niektorého cieľa nič."""
    if exact and any(index.first(t) is None for t in targets):
        return [], None
    days: set[date] = set()
    for target in targets:
        days.update(t.date() for t in (index.times(target) if exact else index.times_any(target)))
    points: list[tuple[datetime, Decimal]] = []
    estimated_until: date | None = None
    estimated_seen = False
    for day in sorted(days):
        moment = datetime.combine(day, time.max, tzinfo=UTC)
        total = manual
        estimated = False
        for target in targets:
            if exact:
                price = index.value_at(target, moment)
                found = None if price is None else (price, True)
            else:
                found = index.value_at_any(target, moment)
            if found is None:
                estimated = True
                total += (index.first(target) if exact else index.first_any(target)) or ZERO
            else:
                total += found[0]
        if estimated:
            estimated_seen = True
        elif estimated_seen and estimated_until is None:
            estimated_until = day
        points.append((datetime.combine(day, time(12), tzinfo=UTC), total))
    return points, estimated_until


def _events(items: list[CollectionItem], num: str) -> list[tuple[date, str, int, Decimal]]:
    """Nákupy (kúpna cena) a predaje (predajná cena) figúrok série po dňoch."""
    grouped: dict[tuple[date, str], list[Decimal]] = defaultdict(list)
    for item in items:
        if item.unidentified or item.catalog is None or series_num(item.catalog, False) != num:
            continue
        if item.purchase_date is not None:
            grouped[(item.purchase_date, "buy")].append(item.purchase_price_eur or ZERO)
        if item.status == ItemStatus.SOLD and item.sold_date is not None:
            grouped[(item.sold_date, "sell")].append(item.sold_price_eur or ZERO)
    return [
        (day, kind, len(amounts), sum(amounts, ZERO))
        for (day, kind), amounts in sorted(grouped.items(), key=lambda e: (e[0][0], e[0][1]))
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
    everything = await load_items(session, user_id)
    events = _events(everything, num)
    items = _mine(everything, num)
    whole = await _whole_series(session, num, {i.catalog_num for i in items})
    if not items:
        return replace(whole, series_size=size, events=events)
    distinct = len({i.catalog_num for i in items})
    owned_count = len(items)
    if single:
        items = _first_of_each(items)
    nums = {resolve_price_target(i, i.catalog).catalog_num for i in items}
    index = await load_snapshots(session, nums)
    valued = value_items(items, index)

    priced = [v for v in valued if v.price_source != "missing"]
    market = [v for v in priced if v.price_source in ("market", "market_approx")]
    manual = sum((v.market_value for v in priced if v.price_source == "manual"), ZERO)
    history, estimated_until = _history(market, manual, index)
    history_used, used_until = _history(market, manual, index, PriceCondition.USED)
    if used_until is not None:
        estimated_until = max(estimated_until or used_until, used_until)
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
        history=history,
        history_used=history_used,
        estimated_until=estimated_until,
        events=events,
        member_count=whole.member_count,
        missing_count=whole.missing_count,
        missing_priced=whole.missing_priced,
        missing_total=whole.missing_total,
        series_priced=whole.series_priced,
        series_total=whole.series_total,
        history_all=whole.history_all,
    )


async def _members(session: AsyncSession, num: str) -> list[str]:
    """Čísla figúrok série; údaj z Rebrickable, bez vlastného kľúča žiadne."""
    vis = visibility.current()
    if not (vis.full or vis.rebrickable):
        return []
    stmt = select(CatalogItem.catalog_num).where(CatalogItem.parent_num == num)
    return sorted((await session.execute(stmt)).scalars())


async def _whole_series(session: AsyncSession, num: str, mine: set[str]) -> SeriesValue:
    """Chýbajúce figúrky a celá séria: každá figúrka raz, cena nového kusu."""
    members = await _members(session, num)
    if not members:
        return SeriesValue()
    index = await load_snapshots(session, set(members))
    targets = {m: PriceTarget(m, PriceKind.SET, PriceCondition.NEW) for m in members}
    prices = {m: index.value_at(t) for m, t in targets.items()}
    known = {m: p for m, p in prices.items() if p is not None}
    missing = [m for m in members if m not in mine]
    missing_known = [known[m] for m in missing if m in known]
    # Len figúrky s cenou: bez nej by jadro nevrátilo nič (exact) a 11 z 12
    # by nemalo graf. Figúrka bez ceny chýba v súčte celý čas, nie skokom.
    history, _ = _sum_history([targets[m] for m in known], ZERO, index, exact=True)
    return SeriesValue(
        member_count=len(members),
        missing_count=len(missing),
        missing_priced=len(missing_known),
        missing_total=sum(missing_known, ZERO) if missing_known else None,
        series_priced=len(known),
        series_total=sum(known.values(), ZERO) if known else None,
        history_all=history,
    )
