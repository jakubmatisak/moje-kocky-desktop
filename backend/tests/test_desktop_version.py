"""Desktop: inštalátor aj zabalený program majú verziu appky.

Zálohu pri aktualizácii spúšťa zmena verzie appky (``lego_api.__version__``
z ``pyproject.toml``, ``test_version.py``). Inštalátor s novým číslom nad
appkou so starým by aktualizáciu bez migrácie nezálohoval a zabalený
program bez metadát balíka by hlásil ``0+unknown``.
"""

import importlib.util
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _app_version() -> str:
    pyproject = (ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(pyproject)["project"]["version"]


def test_installer_default_version_is_app_version():
    # Skript Inno Setup je v UTF-8 s BOM (inak by nečítal diakritiku).
    iss = (ROOT / "packaging" / "moje-kocky.iss").read_text(encoding="utf-8-sig")

    (default,) = re.findall(r'#define AppVersion "([^"]+)"', iss)

    assert default == _app_version()


def test_build_script_default_version_is_app_version():
    script = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8-sig")

    (default,) = re.findall(r'\[string\]\$Version = "([^"]+)"', script)

    assert default == _app_version()


def test_frozen_program_carries_package_metadata():
    """Bez metadát ``importlib.metadata`` v zabalenom programe balík nenájde."""
    spec = (ROOT / "packaging" / "moje-kocky.spec").read_text(encoding="utf-8")

    assert 'copy_metadata("lego-api")' in spec
    # Verzia v Podrobnostiach súboru MojeKocky.exe ide z toho istého zdroja.
    assert "version=version_resource(app_version(ROOT))" in spec


def _version_info():
    spec = importlib.util.spec_from_file_location(
        "version_info", ROOT / "packaging" / "version_info.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strings(resource) -> dict[str, str]:
    (file_info, _translation) = resource.kids
    (table,) = file_info.kids
    return {entry.name: entry.val for entry in table.kids}


def test_exe_version_resource_is_app_version():
    module = _version_info()

    assert module.app_version(ROOT) == _app_version()

    resource = module.version_resource("1.2.3")
    assert (resource.ffi.fileVersionMS, resource.ffi.fileVersionLS) == ((1 << 16) | 2, 3 << 16)
    assert (resource.ffi.productVersionMS, resource.ffi.productVersionLS) == (
        (1 << 16) | 2,
        3 << 16,
    )
    strings = _strings(resource)
    assert strings["ProductVersion"] == strings["FileVersion"] == "1.2.3"
    assert strings["ProductName"] == "Moje kocky"
    assert strings["OriginalFilename"] == "MojeKocky.exe"


def test_exe_version_resource_accepts_local_suffix():
    """Číslo s príveskom (1.0.0rc1) dá v číselnej časti len číslice, text ostane celý."""
    resource = _version_info().version_resource("1.0.0rc1")

    assert (resource.ffi.fileVersionMS, resource.ffi.fileVersionLS) == (1 << 16, 0)
    assert _strings(resource)["ProductVersion"] == "1.0.0rc1"


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell a zostavenie sú len pre Windows")
def test_build_refuses_version_other_than_app_version():
    """Skript skončí skôr, než niečo zostaví.

    PATH bez npm a uv: keby kontrola chýbala, zostavenie aj tak nezačne.
    """
    system32 = Path(os.environ["SYSTEMROOT"]) / "System32"
    powershell = system32 / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    other = "9.9.9"

    result = subprocess.run(
        [
            str(powershell),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "build.ps1"),
            "-Version",
            other,
        ],
        capture_output=True,
        env={**os.environ, "PATH": str(system32)},
        timeout=120,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")

    assert result.returncode != 0
    assert other in output and _app_version() in output, output
    assert "pyproject.toml" in output, output
