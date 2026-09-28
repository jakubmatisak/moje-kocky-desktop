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


def _fatal(data: DataDir) -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(
        None,
        "Moje kocky sa nepodarilo spustiť. Podrobnosti sú v denníku:\n"
        f"{data.logs / 'moje-kocky.log'}",
        TITLE,
        0x10,
    )


def _allow_camera(window) -> None:
    """Skenovanie kamerou: povolenie kamery pre vlastnú stránku appky (file://).

    WebView2 sa inak pri každom spustení pýta a bez kliknutia by čítačka
    nikdy nezačala. Iným adresám (odkazy von sa otvárajú v prehliadači)
    sa nič nepovoľuje.
    """
    try:
        from Microsoft.Web.WebView2.Core import (  # type: ignore[import-not-found]
            CoreWebView2PermissionKind,
            CoreWebView2PermissionState,
        )
        from System import Action  # type: ignore[import-not-found]
    except ImportError:
        logging.warning("WebView2 nie je dostupné, kamera sa nepovolí automaticky")
        return

    def on_permission(sender, args) -> None:
        if args.PermissionKind == CoreWebView2PermissionKind.Camera and str(args.Uri).startswith(
            "file:"
        ):
            args.State = CoreWebView2PermissionState.Allow

    def attach() -> None:
        # Udalosť loaded príde pri každom načítaní stránky; obsluha stačí raz.
        if getattr(window, "_camera_allowed", False):
            return
        window.native.webview.CoreWebView2.PermissionRequested += on_permission
        window._camera_allowed = True

    try:
        window.native.Invoke(Action(attach))
    except Exception:  # noqa: BLE001 - bez automatického povolenia sa appka len opýta
        logging.exception("Povolenie kamery sa nepodarilo nastaviť")


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

    try:
        bridge = Bridge(create_app())
    except Exception:
        logging.exception("Appka sa nepodarilo spustiť")
        _fatal(data)
        lock.release()
        return

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
    window.events.loaded += lambda: _allow_camera(window)
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
