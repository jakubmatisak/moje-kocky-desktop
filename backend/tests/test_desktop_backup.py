"""Desktop: záloha pred aktualizáciou v %APPDATA%\\MojeKocky\\backups.

Databáza desktopu je v priečinku používateľa (``lego_desktop/paths.py``),
zálohy idú vedľa nej, takže ich inštalácia novej verzie ani odinštalovanie
programu nezmažú. Keď štart zlyhá, používateľ nemá konzolu ani log pred
očami: okno so správou mu povie, čo sa stalo a kde je záloha.

Všetky testy majú vlastný %APPDATA% v dočasnom priečinku, skutočné údaje
desktopu ostanú bokom.
"""

import asyncio
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from lego_api.services import db_backup
from lego_desktop import main as desktop_main
from lego_desktop.paths import DataDir

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"
#: Prvá migrácia, existuje vždy a nikdy nebude head.
OLD = "9a38f007d771"


@pytest.fixture
def appdata(tmp_path, monkeypatch) -> Path:
    """Vlastný %APPDATA%; ``DataDir()`` bez argumentu ide sem."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return config


def _head() -> str:
    (head,) = db_backup.head_revisions(_config())
    return head


def _stamp_version(db: Path, version: str) -> None:
    with closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings VALUES ('app_version', ?, '2026-09-01 10:00:00')",
            (json.dumps(version),),
        )
        conn.commit()


def _version_in(db: Path) -> str | None:
    with closing(sqlite3.connect(db)) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'app_version'").fetchone()
    return json.loads(row[0]) if row else None


def _old_database(db: Path) -> None:
    """Revízia bez svojich tabuliek: ďalšia migrácia na nej spadne."""
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sety (num TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        conn.execute("INSERT INTO alembic_version VALUES (?)", (OLD,))
        conn.commit()


def _broken() -> None:
    raise RuntimeError("no such table: users")


# --- kde sú zálohy -----------------------------------------------------------------


def test_backups_folder_is_next_to_the_database_in_appdata(appdata):
    data = DataDir()

    db = db_backup.sqlite_path(data.environment()["DATABASE_URL"])

    assert data.root == appdata / "MojeKocky"
    assert db == data.database
    # Absolútna cesta: relatívna by zálohy dala tam, odkiaľ sa program spustil.
    assert db.is_absolute()
    assert db_backup.failure_marker(db).parent == appdata / "MojeKocky" / "backups"


async def test_new_version_at_startup_backs_up_into_appdata(appdata, settings, monkeypatch):
    """Štart s nastaveniami desktopu nad databázou staršej verzie appky."""
    import lego_api
    from lego_api import main

    data = DataDir()
    monkeypatch.setattr(settings, "database_url", data.environment()["DATABASE_URL"])
    # Skutočná databáza na head, ako ju nechala predchádzajúca verzia.
    # env.py volá asyncio.run, preto mimo slučky testu.
    await asyncio.to_thread(command.upgrade, _config(), "head")
    _stamp_version(data.database, "0.9.0")
    monkeypatch.setattr(lego_api, "__version__", "1.0.0")

    await main._migrate()

    folder = appdata / "MojeKocky" / "backups"
    (name,) = [p.name for p in folder.iterdir()]
    assert re.fullmatch(rf"lego-\d{{8}}-\d{{6}}-v0\.9\.0-{_head()}\.db", name), name
    assert _version_in(data.database) == "1.0.0"
    assert _version_in(folder / name) == "0.9.0"


# --- správa pri zlyhanom štarte --------------------------------------------------


def test_failed_migration_message_names_backup_and_how_to_restore(appdata):
    data = DataDir()
    url = data.environment()["DATABASE_URL"]
    _old_database(data.database)
    with pytest.raises(RuntimeError) as failure:
        db_backup.upgrade_with_backup(url, _config(), _broken, version="1.0.0")
    (saved,) = (appdata / "MojeKocky" / "backups").glob("lego-*.db")

    text = desktop_main.startup_failure_text(data, failure.value)

    assert str(saved) in text
    # Ako vrátiť zálohu: zvyšky žurnálu preč, záloha na miesto databázy.
    assert "lego.db-journal" in text
    assert str(data.database) in text
    assert str(data.logs / "moje-kocky.log") in text


def test_backup_failure_message_says_why(appdata):
    data = DataDir()
    url = data.environment()["DATABASE_URL"]
    _old_database(data.database)
    # Namiesto priečinka záloh súbor: kópia sa nepodarí.
    (data.root / "backups").write_text("nie som priečinok")
    with pytest.raises(db_backup.BackupFailed) as failure:
        db_backup.upgrade_with_backup(url, _config(), _broken, version="1.0.0")

    text = desktop_main.startup_failure_text(data, failure.value)

    assert str(failure.value) in text
    assert str(data.root / "backups") in text
    assert str(data.logs / "moje-kocky.log") in text


def test_other_failure_points_to_the_log(appdata):
    data = DataDir()

    text = desktop_main.startup_failure_text(data, RuntimeError("niečo iné"))

    assert str(data.logs / "moje-kocky.log") in text
    assert "záloh" not in text


def test_startup_failure_shows_the_message(appdata, monkeypatch):
    """``main`` pri páde štartu ukáže správu k tej chybe a pustí zámok."""
    import lego_desktop.bridge

    reason = db_backup.BackupFailed("Záloha databázy pred aktualizáciou zlyhala: plný disk.")

    def failing_bridge(app):
        raise reason

    shown: list[str] = []
    data = DataDir()
    # Premenné, ktoré main nastaví, vráti monkeypatch po teste späť.
    for key in data.environment():
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("LEGO_BACKEND_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setattr(desktop_main, "_logging", lambda data: None)
    monkeypatch.setattr(lego_desktop.bridge, "Bridge", failing_bridge)
    monkeypatch.setattr(desktop_main, "_message_box", lambda text, flags: shown.append(text))

    desktop_main.main()

    assert shown == [desktop_main.startup_failure_text(data, reason)]
    lock = data.lock()
    assert lock is not None
    lock.release()


def test_bridge_passes_startup_failure_on(appdata, settings, monkeypatch):
    """Chyba z lifespan (migrácia) príde do ``main`` ako tá istá výnimka."""
    from lego_api import main
    from lego_desktop.bridge import Bridge

    reason = db_backup.BackupFailed("plný disk")

    async def failing_migrate() -> None:
        raise reason

    monkeypatch.setattr(main, "_migrate", failing_migrate)

    with pytest.raises(db_backup.BackupFailed) as failure:
        Bridge(main.create_app())

    assert failure.value is reason
