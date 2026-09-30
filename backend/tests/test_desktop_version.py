"""Desktop: inštalátor aj zabalený program majú verziu appky.

Zálohu pri aktualizácii spúšťa zmena verzie appky (``lego_api.__version__``
z ``pyproject.toml``, ``test_version.py``). Inštalátor s novým číslom nad
appkou so starým by aktualizáciu bez migrácie nezálohoval a zabalený
program bez metadát balíka by hlásil ``0+unknown``.
"""

import importlib.util
import json
import os
import re
import shutil
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


# --- inštalátor: Vlastnosti → Podrobnosti ------------------------------------------


def test_installer_file_version_is_numbers_of_app_version():
    """Inno Setup chce vo ``VersionInfoVersion`` len čísla, ako Windows v .exe."""
    module = _version_info()

    assert module.file_version("1.2.3") == "1.2.3.0"
    assert module.file_version("1.0.0rc1") == "1.0.0.0"
    assert module.file_version("2") == "2.0.0.0"


def test_build_script_passes_file_version_from_version_info():
    """build.ps1 nepočíta čísla sám, vypíše mu ich ``version_info.py`` (ako MojeKocky.exe)."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "version_info.py"), "1.0.0rc1"],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    script = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8-sig")

    assert result.stdout.strip() == "1.0.0.0"
    assert "version_info.py $Version" in script
    assert '"/DAppFileVersion=$fileVersion"' in script


def _iscc() -> Path | None:
    """ISCC.exe tam, kde ho hľadá build.ps1."""
    found = shutil.which("iscc")
    candidates = [Path(found)] if found else []
    for variable, folder in (
        ("ProgramFiles(x86)", "Inno Setup 6"),
        ("ProgramFiles", "Inno Setup 6"),
        ("LOCALAPPDATA", "Programs/Inno Setup 6"),
    ):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / folder / "ISCC.exe")
    return next((path for path in candidates if path.is_file()), None)


def _file_details(exe: Path) -> dict[str, str]:
    """Verzie z Vlastnosti → Podrobnosti, ako ich číta Windows."""
    command = (
        f"$v = (Get-Item -LiteralPath '{exe}').VersionInfo; "
        "[ordered]@{ file = $v.FileVersion; product = $v.ProductVersion; "
        "fileRaw = $v.FileVersionRaw.ToString(); productRaw = $v.ProductVersionRaw.ToString() }"
        " | ConvertTo-Json"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        timeout=120,
        check=True,
    )
    details = json.loads(result.stdout.decode("utf-8", errors="replace"))
    # Inno Setup dopĺňa texty v zdroji verzie medzerami, Windows ich neukáže.
    return {key: value.strip() for key, value in details.items()}


@pytest.mark.skipif(_iscc() is None, reason="Inno Setup (ISCC.exe) nie je nainštalovaný")
@pytest.mark.parametrize("version", [None, "1.2.3rc1"])
def test_installer_exe_carries_app_version(tmp_path, version):
    """Súbor inštalátora hlási verziu appky, nie 0.0.0.0 (text celý, čísla bez prívesku).

    Zostaví sa len hlavička skutočného skriptu (predvolená verzia a [Setup])
    bez súborov programu, do dočasného priečinka. ``None`` = bez parametrov,
    teda predvolená verzia v skripte; inak tak, ako volá ISCC build.ps1.
    """
    iss = (ROOT / "packaging" / "moje-kocky.iss").read_text(encoding="utf-8-sig")
    header = iss.split("[Languages]", 1)[0]
    # Ikona a licencia s relatívnou cestou ako pri skutočnom skripte.
    header = header.replace("[Setup]\n", f"[Setup]\nSourceDir={ROOT / 'packaging'}\n", 1)
    script = tmp_path / "hlavicka.iss"
    script.write_text(header, encoding="utf-8-sig")
    text = version or _app_version()
    numbers = _version_info().file_version(text)
    defines = [] if version is None else [f"/DAppVersion={text}", f"/DAppFileVersion={numbers}"]

    subprocess.run(
        [str(_iscc()), "/Q", f"/O{tmp_path}", "/Fsetup", *defines, str(script)],
        capture_output=True,
        timeout=300,
        check=True,
    )

    assert _file_details(tmp_path / "setup.exe") == {
        "file": text,
        "product": text,
        "fileRaw": numbers,
        "productRaw": numbers,
    }


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
