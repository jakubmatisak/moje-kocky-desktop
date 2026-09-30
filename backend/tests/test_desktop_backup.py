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
import shutil
import sqlite3
from collections.abc import Callable
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


def _database_of(db: Path, version: str) -> None:
    """Databáza na head, nad ktorou naposledy bežala verzia ``version``."""
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sety (num TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        conn.execute("INSERT INTO alembic_version VALUES (?)", (_head(),))
        conn.execute(
            "CREATE TABLE app_settings (key VARCHAR(64) PRIMARY KEY, value JSON NOT NULL, "
            "updated_at DATETIME NOT NULL)"
        )
        conn.commit()
    _stamp_version(db, version)


def _add_set(db: Path, num: str) -> None:
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO sety VALUES (?)", (num,))
        conn.commit()


def _half_done(db: Path) -> Callable[[], None]:
    """Migrácia, ktorá stihne niečo potvrdiť a potom spadne (SQLite potvrdzuje každú zvlášť)."""
    attempts = 0

    def upgrade() -> None:
        nonlocal attempts
        attempts += 1
        _add_set(db, f"POKAZENE-{attempts}")
        raise RuntimeError("no such table: users")

    return upgrade


def _failed_update(data: DataDir, upgrade: Callable[[], None]) -> Path:
    """Štart verzie 1.1.0, ktorej migrácia spadne; vráti zálohu spred neho."""
    url = data.environment()["DATABASE_URL"]
    with pytest.raises(RuntimeError):
        db_backup.upgrade_with_backup(url, _config(), upgrade, version="1.1.0")
    (saved,) = (data.root / "backups").glob("lego-*.db")
    return saved


def _restore(data: DataDir, saved: Path) -> None:
    """Postup zo správy: zvyšky žurnálu preč, záloha na miesto databázy (čas súboru ostane)."""
    for suffix in ("journal", "wal", "shm"):
        data.database.with_name(f"{data.database.name}-{suffix}").unlink(missing_ok=True)
    shutil.copy2(saved, data.database)


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


def test_repeated_failed_update_still_names_backup_from_before_it(appdata):
    """Ďalší štart tej istej verzie spadne znova: správa ukáže tú istú zálohu."""
    data = DataDir()
    _database_of(data.database, "1.0.0")
    upgrade = _half_done(data.database)
    saved = _failed_update(data, upgrade)
    with pytest.raises(RuntimeError) as failure:
        db_backup.upgrade_with_backup(
            data.environment()["DATABASE_URL"], _config(), upgrade, version="1.1.0"
        )

    text = desktop_main.startup_failure_text(data, failure.value)

    assert list((data.root / "backups").glob("lego-*.db")) == [saved]
    assert str(saved) in text


def test_failure_after_restore_and_more_work_does_not_offer_old_backup(appdata):
    """Záloha späť, predchádzajúca verzia nabehne a používateľ pracuje ďalej.

    Keby neskorší pád z iného dôvodu ukázal starú zálohu ako stav pred
    aktualizáciou, jej návrat by zobral všetko zadané od jej vrátenia.
    """
    data = DataDir()
    _database_of(data.database, "1.0.0")
    saved = _failed_update(data, _half_done(data.database))
    _restore(data, saved)
    url = data.environment()["DATABASE_URL"]
    assert db_backup.upgrade_with_backup(url, _config(), lambda: None, version="1.0.0") is None
    _add_set(data.database, "75192-1")

    text = desktop_main.startup_failure_text(data, RuntimeError("access_backfill spadol"))

    assert str(saved) not in text
    assert "záloh" not in text
    assert str(data.logs / "moje-kocky.log") in text


def test_restored_database_is_not_the_one_the_failed_update_left(appdata):
    """Značka ešte je (stará verzia po návrate nenabehla), no databáza je už iná.

    Pád teraz so zlyhanou aktualizáciou nesúvisí, správa zálohu neponúka.
    """
    data = DataDir()
    _database_of(data.database, "1.0.0")
    saved = _failed_update(data, _half_done(data.database))
    _restore(data, saved)

    text = desktop_main.startup_failure_text(data, RuntimeError("iný pád"))

    assert db_backup.failure_marker(data.database).is_file()
    assert str(saved) not in text
    assert "záloh" not in text


def test_backup_failure_message_says_why(appdata):
    data = DataDir()
    url = data.environment()["DATABASE_URL"]
    _old_database(data.database)
    # Namiesto priečinka záloh súbor: kópia sa nepodarí.
    (data.root / "backups").write_text("nie som priečinok", encoding="utf-8")
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

    received = []

    def failing_bridge(app, remembered=None):
        received.append(remembered)
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
    # Most dostane zapamätané prihlásenie z priečinka údajov.
    assert [r.path for r in received] == [data.session_file]
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
