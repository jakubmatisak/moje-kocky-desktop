"""Úloha v Plánovači úloh Windows pre automatickú obnovu cien.

Úloha `Moje kocky\\Obnova cien - <používateľ>` spustí denne v nastavený čas
`MojeKocky.exe --refresh-prices` bez okna. Beží len v prihlásenom účte
(`InteractiveToken`), takže nikde netreba ukladať heslo, a zmeškaný čas
(vypnutý počítač) dobehne po zapnutí (`StartWhenAvailable`). Vytvára sa
cez `schtasks /XML` v kontexte používateľa, bez práv správcu.
"""

from __future__ import annotations

import getpass
import logging
import subprocess
import sys
import tempfile
from datetime import date, time
from pathlib import Path
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)

#: Priečinok úloh; inštalácia je pre všetkých, každý používateľ Windows má
#: vlastnú úlohu (mená v Plánovači sú spoločné pre počítač a cudziu úlohu
#: bežný používateľ neprepíše). Odinštalovanie zmaže celý priečinok.
TASK_FOLDER = "Moje kocky"
#: Úloha prvej zostavy 1.3.0, ešte bez mena používateľa; pri nastavovaní sa zmaže.
LEGACY_TASK_NAME = f"{TASK_FOLDER}\\Obnova cien"
#: Na volanie schtasks; dlhšie by zdržalo uloženie nastavenia.
TIMEOUT_SECONDS = 15
#: Bez okna konzoly pri volaní schtasks z aplikácie bez konzoly.
_NO_WINDOW = 0x08000000


def task_name() -> str:
    return f"{TASK_FOLDER}\\Obnova cien - {getpass.getuser()}"


class ScheduleError(RuntimeError):
    """Plánovač úloh úlohu nevytvoril ani nezmazal."""


def default_exe() -> Path:
    """Zabalený program je `sys.executable`; z repa sa úloha nevytvára zmysluplne."""
    return Path(sys.executable)


def task_xml(when: time, exe: Path) -> str:
    start = f"{date.today().isoformat()}T{when.strftime('%H:%M')}:00"
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Moje kocky: automatická denná obnova cien.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(exe))}</Command>
      <Arguments>--refresh-prices</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["schtasks", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=TIMEOUT_SECONDS,
        creationflags=_NO_WINDOW if sys.platform == "win32" else 0,
    )


def _forget_legacy_task() -> None:
    """Stará spoločná úloha by bežala popri novej; keď nie je, chyba nevadí."""
    _schtasks("/Delete", "/TN", LEGACY_TASK_NAME, "/F")


def apply(when: time | None, *, exe: Path | None = None) -> None:
    """Vytvorí alebo prestaví úlohu na čas `when`; None úlohu zmaže."""
    _forget_legacy_task()
    if when is None:
        done = _schtasks("/Delete", "/TN", task_name(), "/F")
        if done.returncode != 0:
            # Úloha nebola (vypnuté odjakživa); to je v poriadku.
            log.info("Úloha automatickej obnovy nebola: %s", (done.stderr or "").strip())
        return
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "obnova-cien.xml"
        path.write_text(task_xml(when, exe or default_exe()), encoding="utf-16")
        done = _schtasks("/Create", "/TN", task_name(), "/XML", str(path), "/F")
    if done.returncode != 0:
        raise ScheduleError((done.stderr or done.stdout or "schtasks zlyhal").strip())
    log.info("Úloha automatickej obnovy cien nastavená na %s", when.strftime("%H:%M"))
