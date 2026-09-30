"""Spustenie desktopovej appky: okno bez servera na porte.

Poradie je dôležité: nastavenia appky (lego_api.config) sa čítajú z
prostredia pri prvom importe, preto sa premenné pre %APPDATA% nastavia
skôr, než sa appka naimportuje.
"""

import json
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


#: Ikona okna so správou (MessageBoxW): chyba, informácia.
_ICON_ERROR = 0x10
_ICON_INFO = 0x40


def _message_box(text: str, flags: int) -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, text, TITLE, flags)


def _already_running() -> None:
    _message_box("Moje kocky už bežia. Pozri sa na panel úloh.", _ICON_INFO)


def _failed_update_backup(data: DataDir) -> Path | None:
    """Záloha spred aktualizácie, po ktorej migrácia spadla; inak None.

    Značku (``db_backup.failure_marker``) zapíše appka, keď migrácia po
    zálohe spadne, a zmaže ju po úspešnom štarte. Keď je tu, patrí k tomuto
    pádu (alebo k predchádzajúcemu s tou istou databázou, záloha je tá istá).
    """
    from lego_api.services import db_backup

    marker = db_backup.failure_marker(data.database)
    try:
        name = json.loads(marker.read_text(encoding="utf-8"))["backup"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    saved = marker.parent / str(name)
    if saved.parent != marker.parent or not saved.is_file():
        return None
    return saved


def startup_failure_text(data: DataDir, exc: BaseException) -> str:
    """Správa pre používateľa, keď appka nenabehne.

    Denník ani konzolu nevidí, preto mu správa povie, čo sa stalo: pri
    zlyhanej zálohe dôvod z ``BackupFailed`` (databáza ostala bez zmeny),
    pri zlyhanej migrácii kde je záloha spred aktualizácie a ako ju vrátiť.
    """
    from lego_api.services import db_backup

    details = f"Podrobnosti sú v denníku:\n{data.logs / 'moje-kocky.log'}"
    if isinstance(exc, db_backup.BackupFailed):
        return f"Moje kocky sa nepodarilo spustiť.\n\n{exc}\n\n{details}"
    saved = _failed_update_backup(data)
    if saved is None:
        return f"Moje kocky sa nepodarilo spustiť. {details}"
    db = data.database
    leftovers = ", ".join(f"{db.name}-{suffix}" for suffix in ("journal", "wal", "shm"))
    return (
        "Moje kocky sa nepodarilo spustiť: aktualizácia databázy zlyhala.\n\n"
        f"Zbierka spred aktualizácie je v zálohe:\n{saved}\n\n"
        f"Na návrat zatvor appku, v priečinku {db.parent} zmaž súbory {leftovers}, "
        f"ak tam sú, a zálohu skopíruj na miesto databázy {db}. Kým nebude oprava, "
        "nainštaluj predchádzajúcu verziu appky.\n\n"
        f"{details}"
    )


def _fatal(data: DataDir, exc: BaseException) -> None:
    _message_box(startup_failure_text(data, exc), _ICON_ERROR)


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
    except Exception as exc:
        logging.exception("Appku sa nepodarilo spustiť")
        _fatal(data, exc)
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
