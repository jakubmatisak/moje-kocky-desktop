"""Automatická denná obnova cien: kto je na rade, koľko volá a čo si zapamätá."""

from datetime import datetime, time
from decimal import Decimal

import pytest

from lego_api.config import Settings
from lego_api.models import CatalogItem, CatalogKind, CollectionItem, ItemCondition, User
from lego_api.providers.brickeconomy import quota
from lego_api.services import auto_refresh
from lego_api.services.keys import store
from lego_api.services.refresh import reset_state
from tests.test_refresh import FakeProvider

SETTINGS = Settings(
    jwt_secret="test-secret-test-secret-test-secret-test-secret",
    price_refresh_delay_seconds=0.0,
)
MORNING = datetime(2026, 10, 4, 7, 30)


@pytest.fixture(autouse=True)
def clean():
    reset_state()
    quota.reset()
    auto_refresh.on_schedule_change = None
    yield
    reset_state()
    quota.reset()
    auto_refresh.on_schedule_change = None


def _user(uid: int, prefs: dict | None, *, key: bool = True, fetch: dict | None = None) -> User:
    user = User(id=uid, email=f"u{uid}@x.sk", password_hash="x")
    if prefs is not None:
        user.preferences = {"autoRefresh": prefs}
    if fetch is not None:
        user.fetch_settings = fetch
    if key:
        store(user, "brickeconomy", f"be-key-{uid}", SETTINGS)
    return user


async def _seed(session, *users: User, sets: int = 3) -> None:
    for user in users:
        session.add(user)
    for i in range(sets):
        session.add(CatalogItem(catalog_num=f"1000{i}-1", name=f"Set {i}", kind=CatalogKind.SET))
    await session.flush()
    for user in users:
        for i in range(sets):
            session.add(
                CollectionItem(
                    user_id=user.id,
                    catalog_num=f"1000{i}-1",
                    condition=ItemCondition.NEW_SEALED,
                    flags=[],
                    purchase_price_eur=Decimal("10"),
                )
            )
    await session.commit()


def test_prefs_have_defaults_and_limits() -> None:
    assert auto_refresh.prefs_of(User(email="a@x.sk", password_hash="x")) == auto_refresh.AutoPrefs(
        enabled=False, time=time(7, 0), limit=80
    )
    user = User(email="a@x.sk", password_hash="x")
    user.preferences = {"autoRefresh": {"enabled": True, "time": "21:15", "limit": 500}}
    assert auto_refresh.prefs_of(user) == auto_refresh.AutoPrefs(True, time(21, 15), 100)
    user.preferences = {"autoRefresh": {"enabled": True, "time": "25:99", "limit": 0}}
    assert auto_refresh.prefs_of(user) == auto_refresh.AutoPrefs(True, time(7, 0), 1)


async def test_only_enabled_accounts_with_a_key_whose_time_came_are_due(session) -> None:
    await _seed(
        session,
        _user(1, {"enabled": True, "time": "07:00"}),
        _user(2, {"enabled": True, "time": "08:00"}),
        _user(3, {"enabled": False, "time": "07:00"}),
        _user(4, {"enabled": True, "time": "07:00"}, key=False),
        _user(5, {"enabled": True}, fetch={"disabled": ["brickeconomy.prices"]}),
        _user(6, None),
    )

    due = await auto_refresh.due_users(session, SETTINGS, MORNING)

    assert [u.id for u in due] == [1]


async def test_run_refreshes_with_the_limit_and_remembers_the_day(session, sessionmaker_) -> None:
    await _seed(session, _user(1, {"enabled": True, "time": "07:00", "limit": 2}))
    provider = FakeProvider()

    ran = await auto_refresh.run_due(
        sessionmaker_, SETTINGS, MORNING, provider_for=lambda *_: provider
    )

    assert ran == [1]
    assert len(provider.calls) == 2
    async with sessionmaker_() as s:
        last = await auto_refresh.last_run(s, 1)
    assert last is not None
    assert (last["day"], last["updated"], last["complete"]) == ("2026-10-04", 2, True)

    # Ten istý deň už nie.
    again = await auto_refresh.run_due(
        sessionmaker_, SETTINGS, MORNING, provider_for=lambda *_: provider
    )
    assert again == []
    assert len(provider.calls) == 2


async def test_stopped_run_is_not_complete_and_runs_again_the_same_day(
    session, sessionmaker_
) -> None:
    await _seed(session, _user(1, {"enabled": True, "time": "07:00"}))
    provider = FakeProvider()

    # Otvorená aplikácia požiada o zastavenie po prvom volaní.
    await auto_refresh.run_due(
        sessionmaker_,
        SETTINGS,
        MORNING,
        should_stop=lambda: len(provider.calls) >= 1,
        provider_for=lambda *_: provider,
    )
    async with sessionmaker_() as s:
        last = await auto_refresh.last_run(s, 1)
    assert last is not None
    assert (last["complete"], last["outcome"]) == (False, "stopped")
    assert len(provider.calls) == 1

    rest = await auto_refresh.run_due(
        sessionmaker_, SETTINGS, MORNING, provider_for=lambda *_: provider
    )
    assert rest == [1]
    assert len(provider.calls) == 3


async def test_quota_counter_is_filled_from_todays_logged_calls(session, sessionmaker_) -> None:
    """Nový proces (beh bez okna) nesmie zabudnúť, čo sa dnes už minulo."""
    await _seed(session, _user(1, {"enabled": True, "time": "07:00"}))
    auto_refresh.seed_quota("fp", used=95, limit=100)
    assert quota.remaining(100, "fp") == 5
    auto_refresh.seed_quota("fp", used=10, limit=100)
    assert quota.remaining(100, "fp") == 5


async def test_earliest_time_drives_the_windows_task(session) -> None:
    await _seed(
        session,
        _user(1, {"enabled": True, "time": "08:30"}),
        _user(2, {"enabled": True, "time": "06:45"}),
        _user(3, {"enabled": False, "time": "05:00"}),
    )
    assert await auto_refresh.earliest_time(session, SETTINGS) == time(6, 45)

    applied: list[time | None] = []
    auto_refresh.on_schedule_change = applied.append
    await auto_refresh.sync_schedule(session, SETTINGS)
    assert applied == [time(6, 45)]
