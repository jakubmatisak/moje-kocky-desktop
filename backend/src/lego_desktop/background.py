"""Automatická obnova cien bez okna (`MojeKocky.exe --refresh-prices`).

Spúšťa ju Plánovač úloh Windows. Nad SQLite smie byť jeden proces, preto
beh vezme ten istý zámok ako aplikácia (`DataDir.lock`):
- aplikácia je otvorená: beh hneď skončí, obnovu urobí jej plánovač;
- aplikácia sa otvára počas behu: nájde značku `auto-refresh.running`,
  položí `auto-refresh.stop` a počká na zámok. Beh dokončí rozbehnuté volanie,
  zapíše výsledok (nedokončený) a skončí; zvyšok dobehne otvorená aplikácia.
"""

from __future__ import annotations

import logging
import os
import time as clock
from collections.abc import Callable
from pathlib import Path

from lego_desktop.paths import DataDir, InstanceLock, resource_root

log = logging.getLogger(__name__)

RUNNING = "auto-refresh.running"
STOP = "auto-refresh.stop"

Refresh = Callable[[Callable[[], bool]], object]


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.warning("Značku %s sa nepodarilo zmazať", path)


def run_headless(data: DataDir, *, refresh: Refresh | None = None) -> str:
    """Jeden beh automatickej obnovy. Vráti `app-running` alebo `done`."""
    lock = data.lock()
    if lock is None:
        log.info("Aplikácia je otvorená, automatickú obnovu urobí ona")
        return "app-running"
    running = data.root / RUNNING
    stop_file = data.root / STOP
    _remove(stop_file)
    try:
        running.write_text(str(os.getpid()), encoding="ascii")
        (refresh or _refresh_prices)(stop_file.exists)
    finally:
        _remove(running)
        _remove(stop_file)
        lock.release()
    return "done"


def clear_marks(data: DataDir) -> None:
    """Staré značky po behu, ktorý skončil bez upratania (zámok už drží aplikácia)."""
    _remove(data.root / RUNNING)
    _remove(data.root / STOP)


def wait_for_headless(data: DataDir, *, timeout: float = 30.0) -> InstanceLock | None:
    """Aplikácia sa otvára a zámok drží beh bez okna: požiada ho o koniec a počká.

    Bez značky behu drží zámok iná otvorená aplikácia; vtedy sa nečaká.
    """
    if not (data.root / RUNNING).exists():
        return None
    (data.root / STOP).write_text("stop", encoding="ascii")
    deadline = clock.monotonic() + timeout
    while clock.monotonic() < deadline:
        lock = data.lock()
        if lock is not None:
            return lock
        clock.sleep(0.25)
    return None


def _refresh_prices(should_stop: Callable[[], bool]) -> None:
    """Skutočný beh: migrácie a príprava ako pri štarte, potom `run_due`."""
    import asyncio
    from datetime import datetime

    # Slučka plánovača patrí otvorenej aplikácii, tu sa beží raz.
    os.environ["AUTO_REFRESH_SCHEDULER"] = "false"
    backend_root = resource_root() / "backend"
    if backend_root.is_dir():
        os.environ.setdefault("LEGO_BACKEND_ROOT", str(backend_root))

    from lego_api.config import get_settings
    from lego_api.db import get_sessionmaker
    from lego_api.main import create_app
    from lego_api.services import auto_refresh

    async def go() -> None:
        app = create_app()
        async with app.router.lifespan_context(app):
            ran = await auto_refresh.run_due(
                get_sessionmaker(), get_settings(), datetime.now(), should_stop=should_stop
            )
            log.info("Automatická obnova bez okna: účty %s", ran or "žiadne")

    asyncio.run(go())
