"""Spustenie desktopovej appky: okno bez servera na porte.

Poradie je dôležité: nastavenia appky (lego_api.config) sa čítajú z
prostredia pri prvom importe, preto sa premenné pre %APPDATA% nastavia
skôr, než sa appka naimportuje.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from lego_desktop.paths import DataDir, resource_root

TITLE = "Moje kocky"


def _web_index() -> Path:
    root = resource_root()
    frozen = root / "web" / "index.html"
    if frozen.is_file():
        return frozen
    return root / "frontend" / "dist-desktop" / "index.html"


def _logging(data: DataDir) -> None:
    handler = RotatingFileHandler(
        data.logs / "moje-kocky.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def _already_running() -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(
        None, "Moje kocky už bežia. Pozri sa na panel úloh.", TITLE, 0x40
    )


def main() -> None:
    data = DataDir()
    lock = data.lock()
    if lock is None:
        _already_running()
        return
    _logging(data)
    os.environ.update(data.environment())
    # Migrácie Alembic: pri zabalenom programe sú pribalené vedľa appky.
    backend_root = resource_root() / "backend"
    if backend_root.is_dir():
        os.environ.setdefault("LEGO_BACKEND_ROOT", str(backend_root))

    import webview

    from lego_api.main import create_app
    from lego_desktop.bridge import Bridge

    bridge = Bridge(create_app())

    index = _web_index()
    if not index.is_file():
        logging.error("Chýba zostavený frontend: %s", index)
        sys.exit(1)

    # Bez týchto nastavení by si pywebview pre súbory z disku potichu spustil
    # vlastný server na porte. S nimi sa stránka načíta priamo cez file://.
    webview.settings["ALLOW_FILE_URLS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    window = webview.create_window(
        TITLE, index.as_uri(), js_api=bridge, width=1400, height=900, min_size=(900, 600)
    )

    def choose_save_path(filename: str) -> str | None:
        chosen = window.create_file_dialog(webview.FileDialog.SAVE, save_filename=filename)
        if not chosen:
            return None
        return chosen if isinstance(chosen, str) else chosen[0]

    bridge.choose_save_path = choose_save_path
    icon = resource_root() / "icon.ico"
    try:
        webview.start(
            http_server=False,
            private_mode=False,
            storage_path=str(data.webview),
            icon=str(icon) if icon.is_file() else None,
        )
    finally:
        bridge.close()
        lock.release()


if __name__ == "__main__":
    main()
