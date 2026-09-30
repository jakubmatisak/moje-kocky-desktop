"""Desktop: zapamätané prihlásenie prežije zatvorenie okna.

Okno cookie nemá, obnovovacie cookie drží most. Trvalé cookie (zaškrtnuté
„Zapamätať si prihlásenie na tomto počítači“) most uloží zašifrované do
``session.bin`` v priečinku údajov a pri ďalšom spustení ho vráti klientovi,
takže frontend sa cez ``/auth/refresh`` prihlási sám. Session cookie sa
neukladá. Testy majú vlastný priečinok v ``tmp_path``, nie %APPDATA%.
"""

import asyncio
import base64
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from http.cookiejar import Cookie

import httpx
import pytest
from sqlalchemy import select

from lego_api.models import RefreshToken
from lego_desktop.bridge import Bridge
from lego_desktop.paths import DataDir
from lego_desktop.remember import RememberedLogin

JSON = {"content-type": "application/json"}
EMAIL = "ja@doma.sk"
PASSWORD = "tajneheslo123"


def _body(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _json(response: dict) -> dict:
    return json.loads(base64.b64decode(response["body"]))


@pytest.fixture
def data(tmp_path) -> DataDir:
    return DataDir(tmp_path / "MojeKocky")


@pytest.fixture
def start(engine, sessionmaker_, settings, data):
    """Spustí most nad tou istou databázou; ďalšie volanie = nové spustenie appky."""
    from lego_api import db as db_module
    from lego_api.main import create_app

    db_module._engine = engine
    db_module._sessionmaker = sessionmaker_
    started: list[Bridge] = []

    def _start() -> Bridge:
        # Predošlé okno sa zatvorí; klient httpx a jeho cookies zmiznú s ním.
        for bridge in started:
            bridge.close()
        started.clear()
        app = create_app()

        async def _session_override():
            async with sessionmaker_() as s:
                yield s

        app.dependency_overrides[db_module.get_session] = _session_override
        bridge = Bridge(
            app, run_lifespan=False, remembered=RememberedLogin(data.session_file, settings)
        )
        started.append(bridge)
        return bridge

    yield _start
    for bridge in started:
        bridge.close()
    db_module.reset_engine()


def _register(bridge: Bridge, remember: bool = False, email: str = EMAIL) -> dict:
    response = bridge.request(
        "POST",
        "/api/v1/auth/register",
        JSON,
        _body({"email": email, "password": PASSWORD, "accept_privacy": True, "remember": remember}),
    )
    assert response["status"] == 201, _json(response)
    return _json(response)


def _login(bridge: Bridge, remember: bool) -> dict:
    response = bridge.request(
        "POST",
        "/api/v1/auth/login",
        JSON,
        _body({"email": EMAIL, "password": PASSWORD, "remember": remember}),
    )
    assert response["status"] == 200, _json(response)
    return _json(response)


def _refresh(bridge: Bridge) -> dict:
    return bridge.request("POST", "/api/v1/auth/refresh", {}, None)


def _bearer(token: dict) -> dict:
    return {"authorization": f"Bearer {token['access_token']}"}


def _refresh_cookies(bridge: Bridge) -> list[str]:
    return [c.value for c in bridge._client.cookies.jar if c.name == "lego_refresh"]


def test_session_file_is_in_the_data_folder(data: DataDir) -> None:
    """V %APPDATA%\\MojeKocky: odinštalovanie s mazaním údajov ho zmaže s ostatným."""
    assert data.session_file == data.root / "session.bin"


def test_remembered_login_survives_a_restart(start, data: DataDir) -> None:
    first = start()
    _register(first)
    assert not data.session_file.exists()

    _login(first, remember=True)
    assert data.session_file.is_file()
    # Zašifrované: v súbore nie je cookie, ktoré server poslal.
    [cookie] = _refresh_cookies(first)
    assert cookie not in data.session_file.read_text(encoding="ascii")

    again = start()
    refreshed = _refresh(again)
    assert refreshed["status"] == 200, _json(refreshed)
    me = again.request("GET", "/api/v1/auth/me", _bearer(_json(refreshed)), None)
    assert _json(me)["email"] == EMAIL
    # Obnova token vymení: v klientovi ostane jediné cookie a uloží sa nové.
    assert len(_refresh_cookies(again)) == 1
    assert _refresh(again)["status"] == 200
    assert len(_refresh_cookies(again)) == 1

    assert _refresh(start())["status"] == 200


def test_login_without_remember_stores_nothing(start, data: DataDir) -> None:
    bridge = start()
    _register(bridge)
    _login(bridge, remember=False)
    assert _refresh(bridge)["status"] == 200
    assert not data.session_file.exists()

    assert _refresh(start())["status"] == 401


def test_login_without_remember_forgets_an_earlier_remembered_one(start, data: DataDir) -> None:
    bridge = start()
    _register(bridge, remember=True)
    assert data.session_file.is_file()

    _login(bridge, remember=False)
    assert not data.session_file.exists()


def test_logout_deletes_the_file(start, data: DataDir) -> None:
    bridge = start()
    _register(bridge, remember=True)
    assert data.session_file.is_file()

    assert bridge.request("POST", "/api/v1/auth/logout", {}, None)["status"] == 204
    assert not data.session_file.exists()
    assert _refresh(start())["status"] == 401


def test_password_change_keeps_the_remembered_login_with_a_new_token(start, data: DataDir) -> None:
    """Zmena hesla zruší všetky prihlásenia účtu, toto okno nové heslo pozná.

    Server mu vydá nový token v tom istom režime (zapamätaný ostane
    zapamätaný), most ho uloží namiesto starého. Starý token už nič neotvorí.
    """
    bridge = start()
    token = _register(bridge, remember=True)
    [old] = _refresh_cookies(bridge)
    saved_before = data.session_file.read_bytes()

    changed = bridge.request(
        "PATCH",
        "/api/v1/auth/me",
        {**JSON, **_bearer(token)},
        _body({"current_password": PASSWORD, "new_password": "noveheslo123"}),
    )
    assert changed["status"] == 200, _json(changed)
    [new] = _refresh_cookies(bridge)
    assert new != old
    assert data.session_file.is_file()
    assert data.session_file.read_bytes() != saved_before

    # Starý token (napr. skopírovaný súbor spred zmeny) neplatí; toto okno
    # drží nový, takže odmietnutie starého súbor nezmaže.
    stale = bridge.request("POST", "/api/v1/auth/refresh", {"cookie": f"lego_refresh={old}"}, None)
    assert stale["status"] == 401
    assert data.session_file.is_file()

    assert _refresh(bridge)["status"] == 200
    assert _refresh(start())["status"] == 200


def test_deleting_the_account_deletes_the_file(start, data: DataDir) -> None:
    bridge = start()
    admin = _register(bridge)
    opened = bridge.request(
        "PATCH",
        "/api/v1/admin/settings",
        {**JSON, **_bearer(admin)},
        _body({"allow_registration": True}),
    )
    assert opened["status"] == 200, _json(opened)
    token = _register(bridge, remember=True, email="druhy@doma.sk")
    assert data.session_file.is_file()

    gone = bridge.request(
        "DELETE", "/api/v1/auth/me", {**JSON, **_bearer(token)}, _body({"password": PASSWORD})
    )
    assert gone["status"] == 204, _json(gone)
    assert not data.session_file.exists()


async def _expire_all(sessionmaker_) -> None:
    async with sessionmaker_() as s:
        for token in (await s.scalars(select(RefreshToken))).all():
            token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await s.commit()


def test_refused_refresh_deletes_the_file(start, data: DataDir, sessionmaker_) -> None:
    """Vypršané zapamätanie (30 dní bez použitia): appka sa opýta heslo a súbor zmizne."""
    _register(start(), remember=True)
    asyncio.run(_expire_all(sessionmaker_))

    again = start()
    assert _refresh(again)["status"] == 401
    assert not data.session_file.exists()


def test_stale_cookie_within_grace_keeps_the_remembered_login(start, data: DataDir) -> None:
    """Dve obnovy naraz (pywebview volá most z viacerých vlákien).

    Neskoršia príde so starým cookie do ochrannej lehoty: dostane prístup
    aj vlastné nové cookie, most ho uloží a zapamätanie ostane platné.
    """
    bridge = start()
    _register(bridge, remember=True)
    [stale] = _refresh_cookies(bridge)
    assert _refresh(bridge)["status"] == 200
    [current] = _refresh_cookies(bridge)
    saved = data.session_file.read_bytes()

    late = bridge.request("POST", "/api/v1/auth/refresh", {"cookie": f"lego_refresh={stale}"}, None)
    assert late["status"] == 200, _json(late)
    assert "access_token" in _json(late)
    assert "set-cookie" in late["headers"]
    assert data.session_file.is_file()
    assert data.session_file.read_bytes() != saved
    assert _refresh_cookies(bridge) != [current]
    assert _refresh(start())["status"] == 200


async def _age_revoked(sessionmaker_, seconds: int) -> None:
    async with sessionmaker_() as s:
        for token in (await s.scalars(select(RefreshToken))).all():
            if token.revoked_at is not None:
                token.revoked_at = datetime.now(UTC) - timedelta(seconds=seconds)
        await s.commit()


def test_copied_cookie_used_first_ends_the_remembered_login(
    start, data: DataDir, sessionmaker_, settings
) -> None:
    """Niekto skopíroval cookie a obnovil prvý; okno príde s ním po lehote.

    Server zruší všetky prihlásenia účtu a most súbor zmaže: okno poslalo
    to cookie, ktoré drží, takže nejde o súbeh dvoch obnov.
    """
    bridge = start()
    _register(bridge, remember=True)
    [copied] = _refresh_cookies(bridge)

    async def thief() -> int:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=bridge._app), base_url="http://desktop"
        ) as other:
            other.cookies.set("lego_refresh", copied)
            return (await other.post("/api/v1/auth/refresh")).status_code

    assert bridge._run(thief()) == 200
    asyncio.run(_age_revoked(sessionmaker_, settings.refresh_grace_seconds + 60))

    assert _refresh(bridge)["status"] == 401
    assert not data.session_file.exists()
    assert _refresh(start())["status"] == 401


def test_corrupt_file_is_deleted_quietly(start, data: DataDir) -> None:
    data.session_file.write_bytes(b"\x00\xffnie je to fernet")
    bridge = start()
    assert not data.session_file.exists()
    assert _refresh(bridge)["status"] == 401


def test_file_from_another_secret_is_deleted(start, data: DataDir, settings, monkeypatch) -> None:
    """Iný secret.key (napr. obnovená databáza bez neho): súbor sa nedá prečítať."""
    _register(start(), remember=True)
    assert data.session_file.is_file()

    monkeypatch.setattr(settings, "jwt_secret", "iny-tajny-kluc-dlhy-aspon-32-znakov!")
    start()
    assert not data.session_file.exists()


def test_expired_file_is_not_loaded(data: DataDir, settings) -> None:
    remembered = RememberedLogin(data.session_file, settings)
    past = int((datetime.now(UTC) - timedelta(days=1)).timestamp())
    cookie = Cookie(
        version=0,
        name="lego_refresh",
        value="x",
        port=None,
        port_specified=False,
        domain="desktop.local",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=past,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
    )
    remembered.save(cookie)
    assert data.session_file.is_file()
    assert remembered.load() is None
    assert not data.session_file.exists()


def test_export_does_not_carry_the_remembered_login(start, data: DataDir) -> None:
    bridge = start()
    token = _register(bridge, remember=True)
    [cookie] = _refresh_cookies(bridge)
    exported = bridge.request("GET", "/api/v1/auth/me/export", _bearer(token), None)
    assert exported["status"] == 200
    content = base64.b64decode(exported["body"])
    archive = zipfile.ZipFile(io.BytesIO(content))
    assert not [n for n in archive.namelist() if "session" in n]
    assert cookie.encode() not in content
    assert data.session_file.read_bytes() not in content


def test_the_app_remembers_into_its_data_folder(data: DataDir, settings) -> None:
    """Spustenie appky dá mostu súbor v priečinku údajov a tajomstvo zo secret.key."""
    from lego_desktop.main import remembered_login

    remembered = remembered_login(data)
    assert remembered.path == data.session_file
    assert remembered._settings.jwt_secret == settings.jwt_secret
