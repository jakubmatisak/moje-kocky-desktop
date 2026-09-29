"""Licenčné texty softvéru tretích strán, ktoré ide s inštalátorom.

MIT, BSD aj Apache chcú, aby šírený program niesol ich text. Generátor
(`packaging/notices.py`) ich zbiera z nainštalovaných balíkov Pythonu
a z `package-lock.json` frontendu, bez siete.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _notices():
    spec = importlib.util.spec_from_file_location("notices", ROOT / "packaging" / "notices.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["notices"] = module  # dataclass si modul hľadá v sys.modules
    spec.loader.exec_module(module)
    return module


def test_python_entries_are_runtime_closure_with_texts():
    entries = {e.name.lower(): e for e in _notices().python_entries("lego-api")}
    for name in ("fastapi", "starlette", "pywebview", "pythonnet", "sqlalchemy", "pillow"):
        assert name in entries, name
        assert len(entries[name].text) > 200, name
    # Extra pydantic[email] ťahá email-validator.
    assert "email-validator" in entries
    # Vývojové nástroje do programu nejdú.
    for dev in ("pytest", "ruff", "mypy", "respx"):
        assert dev not in entries
    # Balíky len pre iné systémy tu nie sú nainštalované.
    assert not any(n.startswith("pyobjc") for n in entries)


def test_pyinstaller_bootloader_is_listed_with_its_exception():
    entry = _notices().pyinstaller_entry()
    assert entry.name == "PyInstaller"
    assert "bootloader" in entry.text.lower()


def test_npm_entries_skip_dev_packages():
    entries = {e.name: e for e in _notices().npm_entries(ROOT / "frontend")}
    for name in ("vue", "vuetify", "chart.js", "zxing-wasm", "@mdi/font", "@fontsource/roboto"):
        assert name in entries, name
        assert entries[name].text.strip(), name
    for dev in ("vite", "eslint", "vitest", "typescript"):
        assert dev not in entries
    # Zostavovacie nástroje v programe nie sú, aj keď ich zámok neoznačí ako dev.
    assert not any(n.startswith(("@rolldown/", "sass", "lightningcss")) for n in entries)


def test_render_starts_with_python_and_app_license():
    text = _notices().render(ROOT)
    assert text.startswith("Moje kocky Desktop")
    assert "PYTHON SOFTWARE FOUNDATION LICENSE" in text
    assert "fastapi" in text.lower()
    assert "vuetify" in text.lower()
