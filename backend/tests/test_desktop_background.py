"""Automatická obnova bez okna: zámok, značky a ustúpenie otvorenej aplikácii."""

import threading
import time as clock

from lego_desktop import background
from lego_desktop.paths import DataDir


def test_headless_run_skips_when_the_app_is_open(tmp_path) -> None:
    data = DataDir(tmp_path)
    app_lock = data.lock()
    assert app_lock is not None
    ran: list[str] = []

    try:
        result = background.run_headless(data, refresh=lambda stop: ran.append("run"))
    finally:
        app_lock.release()

    assert result == "app-running"
    assert ran == []


def test_headless_run_marks_itself_and_cleans_up(tmp_path) -> None:
    data = DataDir(tmp_path)
    seen: list[bool] = []

    def refresh(stop) -> None:
        seen.append((tmp_path / background.RUNNING).exists())
        seen.append(stop())

    assert background.run_headless(data, refresh=refresh) == "done"
    assert seen == [True, False]
    assert not (tmp_path / background.RUNNING).exists()
    assert not (tmp_path / background.STOP).exists()
    # Zámok je voľný, aplikácia sa môže otvoriť.
    lock = data.lock()
    assert lock is not None
    lock.release()


def test_opening_the_app_asks_the_headless_run_to_stop(tmp_path) -> None:
    data = DataDir(tmp_path)
    started = threading.Event()

    def refresh(stop) -> None:
        started.set()
        deadline = clock.monotonic() + 5
        while not stop() and clock.monotonic() < deadline:
            clock.sleep(0.02)

    worker = threading.Thread(
        target=background.run_headless, args=(data,), kwargs={"refresh": refresh}
    )
    worker.start()
    assert started.wait(2)

    lock = background.wait_for_headless(data, timeout=5)
    worker.join(5)

    assert lock is not None
    lock.release()


def test_without_a_headless_run_the_app_does_not_wait(tmp_path) -> None:
    data = DataDir(tmp_path)
    other = data.lock()
    assert other is not None
    try:
        began = clock.monotonic()
        assert background.wait_for_headless(data, timeout=5) is None
        assert clock.monotonic() - began < 1
    finally:
        other.release()


def test_main_with_refresh_prices_runs_without_a_window(monkeypatch, tmp_path) -> None:
    from lego_desktop import main as desktop_main

    calls: list[object] = []
    monkeypatch.setattr(desktop_main, "DataDir", lambda: DataDir(tmp_path))
    monkeypatch.setattr(background, "run_headless", lambda data: calls.append(data.root))
    monkeypatch.setattr(desktop_main.sys, "argv", ["MojeKocky.exe", "--refresh-prices"])
    for key in DataDir(tmp_path).environment():
        monkeypatch.delenv(key, raising=False)

    desktop_main.main()

    assert calls == [tmp_path]
