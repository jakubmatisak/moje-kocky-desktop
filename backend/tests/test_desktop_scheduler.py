"""Úloha v Plánovači úloh Windows pre automatickú obnovu cien."""

import xml.etree.ElementTree as ET
from datetime import time
from pathlib import Path

from lego_desktop import scheduler

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
EXE = Path(r"C:\Program Files\MojeKocky\MojeKocky.exe")


def test_task_xml_runs_daily_at_the_time_only_when_logged_on() -> None:
    root = ET.fromstring(scheduler.task_xml(time(6, 45), EXE).encode("utf-16"))

    start = root.find("t:Triggers/t:CalendarTrigger/t:StartBoundary", NS)
    assert start is not None and start.text is not None and start.text.endswith("T06:45:00")
    assert root.find("t:Triggers/t:CalendarTrigger/t:ScheduleByDay/t:DaysInterval", NS).text == "1"
    assert root.find("t:Principals/t:Principal/t:LogonType", NS).text == "InteractiveToken"
    assert root.find("t:Settings/t:StartWhenAvailable", NS).text == "true"
    assert root.find("t:Settings/t:DisallowStartIfOnBatteries", NS).text == "false"
    assert root.find("t:Settings/t:ExecutionTimeLimit", NS).text == "PT30M"
    assert root.find("t:Actions/t:Exec/t:Command", NS).text == str(EXE)
    assert root.find("t:Actions/t:Exec/t:Arguments", NS).text == "--refresh-prices"


def test_apply_creates_the_task_from_xml_and_deletes_it(monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []
    written: list[str] = []

    def run(args, **kwargs):
        calls.append(list(args))
        if "/XML" in args:
            written.append(Path(args[args.index("/XML") + 1]).read_text(encoding="utf-16"))

        class Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return Done()

    monkeypatch.setattr(scheduler.subprocess, "run", run)

    scheduler.apply(time(7, 0), exe=EXE)
    scheduler.apply(None, exe=EXE)

    assert calls[0][:4] == ["schtasks", "/Create", "/TN", scheduler.task_name()]
    assert calls[0][-1] == "/F"
    assert "T07:00:00" in written[0]
    assert calls[1] == ["schtasks", "/Delete", "/TN", scheduler.task_name(), "/F"]


def test_every_windows_user_has_an_own_task(monkeypatch) -> None:
    """Inštalácia je pre všetkých, mená úloh v Plánovači sú spoločné pre počítač."""
    monkeypatch.setattr(scheduler.getpass, "getuser", lambda: "Jakub")
    assert scheduler.task_name() == r"Moje kocky\Obnova cien - Jakub"
    monkeypatch.setattr(scheduler.getpass, "getuser", lambda: "Anna")
    assert scheduler.task_name() == r"Moje kocky\Obnova cien - Anna"


def test_schtasks_has_a_time_limit(monkeypatch) -> None:
    seen: list[dict] = []

    def run(args, **kwargs):
        seen.append(kwargs)

        class Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return Done()

    monkeypatch.setattr(scheduler.subprocess, "run", run)
    scheduler.apply(None, exe=EXE)
    assert seen[0]["timeout"] == 15


def test_apply_reports_a_failing_schtasks(monkeypatch) -> None:
    def run(args, **kwargs):
        class Failed:
            returncode = 1
            stdout = ""
            stderr = "Access is denied."

        return Failed()

    monkeypatch.setattr(scheduler.subprocess, "run", run)

    try:
        scheduler.apply(time(7, 0), exe=EXE)
    except scheduler.ScheduleError as exc:
        assert "Access is denied" in str(exc)
    else:
        raise AssertionError("chyba schtasks sa mala ohlásiť")


def test_missing_task_on_delete_is_fine(monkeypatch) -> None:
    def run(args, **kwargs):
        class Missing:
            returncode = 1
            stdout = ""
            stderr = "ERROR: The system cannot find the file specified."

        return Missing()

    monkeypatch.setattr(scheduler.subprocess, "run", run)

    scheduler.apply(None, exe=EXE)
