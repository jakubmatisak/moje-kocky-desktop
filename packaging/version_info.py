"""Verzia v súbore MojeKocky.exe (Vlastnosti → Podrobnosti) z ``pyproject.toml``.

Jediný zdroj verzie appky je ``backend/pyproject.toml`` (``lego_api.__version__``).
PyInstaller (``moje-kocky.spec``) ju odtiaľto zapíše aj do .exe, aby súbor
hlásil to isté ako appka a inštalátor.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from PyInstaller.utils.win32 import versioninfo as vi

#: Slovenčina (0x041B), Unicode (1200); v zdroji verzie ako „041B04B0“.
_LANGUAGE = 0x041B
_CODEPAGE = 1200


def app_version(root: Path) -> str:
    """Verzia appky z ``backend/pyproject.toml`` v koreni repozitára ``root``."""
    pyproject = (Path(root) / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(pyproject)["project"]["version"]


def _numbers(version: str) -> tuple[int, int, int, int]:
    """Štyri čísla pre Windows: len úvodné ``a.b.c``, prívesok (rc1) nie."""
    match = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if match is None:
        return (0, 0, 0, 0)
    major, minor, patch = (int(part or 0) for part in match.groups())
    return (major, minor, patch, 0)


def version_resource(version: str) -> vi.VSVersionInfo:
    numbers = _numbers(version)
    strings = [
        vi.StringStruct("CompanyName", "jakubmatisak"),
        vi.StringStruct("FileDescription", "Moje kocky"),
        vi.StringStruct("FileVersion", version),
        vi.StringStruct("InternalName", "MojeKocky"),
        vi.StringStruct("OriginalFilename", "MojeKocky.exe"),
        vi.StringStruct("ProductName", "Moje kocky"),
        vi.StringStruct("ProductVersion", version),
    ]
    return vi.VSVersionInfo(
        ffi=vi.FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            vi.StringFileInfo([vi.StringTable(f"{_LANGUAGE:04X}{_CODEPAGE:04X}", strings)]),
            vi.VarFileInfo([vi.VarStruct("Translation", [_LANGUAGE, _CODEPAGE])]),
        ],
    )
