"""Automatická denná obnova cien (desktop).

Používateľ ju zapne pri účte (`preferences.autoRefresh`: prepínač, čas,
počet). Spúšťa ju Plánovač úloh Windows (`MojeKocky.exe --refresh-prices`)
alebo otvorená aplikácia, ktorá raz za minútu skontroluje, komu nastal čas.
Oba idú cez `run_due`, teda cez tú istú obnovu ako tlačidlo v lište:
vek ceny, najprv neznáme, zvyšok kvóty a rezerva.

Čas sa porovnáva s miestnym časom počítača. Výsledok posledného behu je
v `app_settings` (`auto_refresh_last`) podľa účtu; prerušený beh
(`complete=False`) v ten deň dobehne, dokončený sa neopakuje.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lego_api import api_log
from lego_api.capabilities import Cap
from lego_api.config import Settings
from lego_api.models import AppSetting, User
from lego_api.providers.brickeconomy import BrickEconomyProvider, quota
from lego_api.routers.usage import brickeconomy_used
from lego_api.services.keys import keys_of
from lego_api.services.refresh import claim, refresh_prices

log = logging.getLogger(__name__)

DEFAULT_TIME = time(7, 0)
DEFAULT_LIMIT = 80
#: Najviac toľko volaní na beh; viac denný limit BrickEconomy aj tak nedá.
MAX_LIMIT = 100
LAST_KEY = "auto_refresh_last"

#: Desktop sem dá funkciu, ktorá nastaví úlohu v Plánovači úloh Windows
#: (najskorší čas zo zapnutých účtov, None = zmazať). Web ju nemá.
on_schedule_change: Callable[[time | None], None] | None = None


@dataclass(frozen=True)
class AutoPrefs:
    enabled: bool
    time: time
    limit: int


def _parse_time(value: object) -> time:
    if isinstance(value, str):
        try:
            hours, minutes = value.split(":")
            return time(int(hours), int(minutes))
        except ValueError:
            pass
    return DEFAULT_TIME


def prefs_of(user: User) -> AutoPrefs:
    """Nastavenie účtu s predvolenými hodnotami; nezmyselná hodnota = predvolená."""
    raw = (user.preferences or {}).get("autoRefresh") or {}
    limit = raw.get("limit")
    if not isinstance(limit, int) or isinstance(limit, bool):
        limit = DEFAULT_LIMIT
    return AutoPrefs(
        enabled=raw.get("enabled") is True,
        time=_parse_time(raw.get("time")),
        limit=max(1, min(MAX_LIMIT, limit)),
    )


def _allowed(user: User, settings: Settings) -> bool:
    """Kľúč BrickEconomy a zapnutá schopnosť dávky; bez nich sa nevolá nič."""
    keys = keys_of(user, settings)
    return bool(keys.brickeconomy) and keys.policy.enabled(Cap.BRICKECONOMY_PRICES)


async def _all_last(session: AsyncSession) -> dict:
    row = await session.get(AppSetting, LAST_KEY)
    return dict(row.value) if row is not None and isinstance(row.value, dict) else {}


async def last_run(session: AsyncSession, user_id: int) -> dict | None:
    """Posledný automatický beh účtu (čas, deň, obnovené, výsledok, dokončený)."""
    return (await _all_last(session)).get(str(user_id))


async def _remember(session: AsyncSession, user_id: int, record: dict) -> None:
    value = await _all_last(session)
    value[str(user_id)] = record
    row = await session.get(AppSetting, LAST_KEY)
    if row is None:
        session.add(AppSetting(key=LAST_KEY, value=value))
    else:
        row.value = value
    await session.commit()


async def _enabled_users(session: AsyncSession, settings: Settings) -> list[User]:
    users = (await session.execute(select(User).order_by(User.id))).scalars().all()
    return [u for u in users if u.is_active and prefs_of(u).enabled and _allowed(u, settings)]


async def due_users(session: AsyncSession, settings: Settings, now: datetime) -> list[User]:
    """Zapnuté účty s kľúčom, ktorým nastal čas a dnes ešte nemajú celý beh."""
    last = await _all_last(session)
    today = now.date().isoformat()
    due: list[User] = []
    for user in await _enabled_users(session, settings):
        if now.time() < prefs_of(user).time:
            continue
        record = last.get(str(user.id)) or {}
        if record.get("day") == today and record.get("complete"):
            continue
        due.append(user)
    return due


def seed_quota(key_id: str, *, used: int, limit: int) -> None:
    """Počítadlo kvóty v procese nikdy pod dnešné zapísané volania (nový proces)."""
    quota.seed(limit, key_id, used)


async def run_due(
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    now: datetime,
    *,
    should_stop: Callable[[], bool] | None = None,
    provider_for: Callable[[Settings, object], object] = BrickEconomyProvider.for_user,
) -> list[int]:
    """Obnoví ceny účtom, ktoré sú na rade. Vráti ich čísla."""
    async with sessionmaker() as session:
        due = await due_users(session, settings, now)
    ran: list[int] = []
    for user in due:
        if should_stop is not None and should_stop():
            break
        prefs = prefs_of(user)
        keys = keys_of(user, settings)
        provider = provider_for(settings, keys)
        api_log.set_user(user.id)
        fingerprint = getattr(provider, "fingerprint", None)
        if fingerprint and isinstance(provider, BrickEconomyProvider):
            async with sessionmaker() as session:
                used = await brickeconomy_used(session, user.id, settings, provider)
            seed_quota(fingerprint, used=used, limit=settings.brickeconomy_daily_limit)
        if await claim(user.id) is None:
            # Práve beží ručná obnova; plánovač to skúsi o minútu.
            continue
        stopped = False

        def stop() -> bool:
            nonlocal stopped
            if should_stop is not None and should_stop():
                stopped = True
            return stopped

        outcome = "ok"
        try:
            state = await refresh_prices(
                sessionmaker,
                user.id,
                settings,
                provider,  # type: ignore[arg-type]
                limit=prefs.limit,
                claimed=True,
                should_stop=stop,
            )
            if state.last_error:
                known = ("quota", "reserve", "disabled")
                outcome = state.last_error if state.last_error in known else "error"
            updated = state.updated
        except Exception:  # noqa: BLE001 - jeden účet nesmie zastaviť ostatné
            log.exception("Automatická obnova cien účtu %s zlyhala", user.id)
            outcome, updated = "error", 0
        if stopped:
            outcome = "stopped"
        async with sessionmaker() as session:
            await _remember(
                session,
                user.id,
                {
                    "at": now.isoformat(timespec="minutes"),
                    "day": now.date().isoformat(),
                    "updated": updated,
                    "outcome": outcome,
                    "complete": not stopped,
                },
            )
        ran.append(user.id)
        log.info("Automatická obnova cien účtu %s: %s, obnovené %s", user.id, outcome, updated)
    return ran


async def earliest_time(session: AsyncSession, settings: Settings) -> time | None:
    """Čas úlohy v Plánovači: najskorší zo zapnutých účtov s kľúčom."""
    times = [prefs_of(u).time for u in await _enabled_users(session, settings)]
    return min(times) if times else None


async def sync_schedule(session: AsyncSession, settings: Settings) -> None:
    """Prestaví úlohu v Plánovači podľa nastavení; chyba nesmie zhodiť volajúceho."""
    if on_schedule_change is None:
        return
    when = await earliest_time(session, settings)
    try:
        on_schedule_change(when)
    except Exception:  # noqa: BLE001 - nastavenie sa uloží aj bez úlohy
        log.exception("Úlohu automatickej obnovy cien sa nepodarilo nastaviť")
