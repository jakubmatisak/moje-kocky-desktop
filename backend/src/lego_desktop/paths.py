"""Kde má desktopová appka svoje údaje: %APPDATA%\\MojeKocky.

Databáza, fotky, tajomstvo na šifrovanie kľúčov a denníky sú v priečinku
používateľa, nie pri programe: inštalácia novej verzie ich tak neprepíše a
odinštalovanie ich nechá (ak si ich používateľ nezmaže sám).
"""

import msvcrt
import os
import secrets
import sys
from pathlib import Path

APP_FOLDER = "MojeKocky"


def default_root() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_FOLDER


class InstanceLock:
    """Zámok proti druhému spusteniu (dva procesy nad jednou SQLite)."""

    def __init__(self, handle) -> None:
        self._handle = handle

    def release(self) -> None:
        try:
            self._handle.seek(0)
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self._handle.close()


class DataDir:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_root()
        self.photos = self.root / "photos"
        self.logs = self.root / "logs"
        self.webview = self.root / "webview"
        for folder in (self.root, self.photos, self.logs, self.webview):
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def database(self) -> Path:
        return self.root / "lego.db"

    @property
    def session_file(self) -> Path:
        """Zapamätané prihlásenie (``lego_desktop.remember``), len keď si ho používateľ zvolí."""
        return self.root / "session.bin"

    def secret(self) -> str:
        """Tajomstvo na šifrovanie kľúčov a podpis tokenov; vznikne pri prvom spustení.

        Keby sa stratilo, uložené kľúče k službám sa nedajú prečítať a treba
        ich zadať znova (zbierka ostane).
        """
        path = self.root / "secret.key"
        if path.is_file():
            value = path.read_text(encoding="ascii").strip()
            if len(value) >= 48:
                return value
        value = secrets.token_urlsafe(48)
        path.write_text(value, encoding="ascii")
        return value

    def environment(self) -> dict[str, str]:
        """Premenné pre nastavenia appky (lego_api.config) v desktopovom režime."""
        return {
            "DATABASE_URL": f"sqlite+aiosqlite:///{self.database.as_posix()}",
            "PHOTOS_DIR": str(self.photos),
            "JWT_SECRET": self.secret(),
            # Prvý účet vznikne vždy; ďalší len keď to správca v appke povolí.
            "ALLOW_REGISTRATION": "false",
        }

    def lock(self) -> InstanceLock | None:
        """Zamkne priečinok pre tento proces; None = appka už beží."""
        handle = open(self.root / "instance.lock", "a+")  # noqa: SIM115 - drží sa do konca
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return None
        return InstanceLock(handle)


def resource_root() -> Path:
    """Kde sú pribalené súbory: pri zabalenom programe PyInstaller, inak repo."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parents[3]
