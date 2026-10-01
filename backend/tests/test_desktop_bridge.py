"""Desktop: okno volá appku cez most v tom istom procese, bez portu."""

import asyncio
import base64
import json
import os
import subprocess
import sys
import threading

import pytest

import lego_api
from lego_desktop.bridge import Bridge
from lego_desktop.paths import DataDir


def _body(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _json(response: dict) -> dict:
    return json.loads(base64.b64decode(response["body"]))


@pytest.fixture
def bridge(engine, sessionmaker_, settings):
    from lego_api import db as db_module
    from lego_api.main import create_app

    db_module._engine = engine
    db_module._sessionmaker = sessionmaker_
    app = create_app()

    async def _session_override():
        async with sessionmaker_() as s:
            yield s

    app.dependency_overrides[db_module.get_session] = _session_override
    started = Bridge(app, run_lifespan=False)
    yield started
    started.close()
    db_module.reset_engine()


JSON = {"content-type": "application/json"}


def test_request_goes_to_the_app_and_keeps_the_session_cookie(bridge: Bridge) -> None:
    health = bridge.request("GET", "/api/v1/health", {}, None)
    assert health["status"] == 200
    assert _json(health) == {"status": "ok", "version": lego_api.__version__}

    reg = bridge.request(
        "POST",
        "/api/v1/auth/register",
        JSON,
        _body({"email": "ja@doma.sk", "password": "tajneheslo123", "accept_privacy": True}),
    )
    assert reg["status"] == 201, _json(reg)
    # Obnovovacie cookie drží most, prehliadač ho nemá.
    refreshed = bridge.request("POST", "/api/v1/auth/refresh", {}, None)
    assert refreshed["status"] == 200
    token = _json(refreshed)["access_token"]
    me = bridge.request("GET", "/api/v1/auth/me", {"authorization": f"Bearer {token}"}, None)
    assert _json(me)["email"] == "ja@doma.sk"


def test_errors_and_query_strings_pass_through(bridge: Bridge) -> None:
    missing = bridge.request("GET", "/api/v1/auth/me", {}, None)
    assert missing["status"] == 401
    bad = bridge.request("GET", "/api/v1/img?u=https%3A%2F%2Fevil.example%2Fa.jpg", {}, None)
    assert bad["status"] == 400


def test_repeated_query_parameter_reaches_the_app_whole(bridge: Bridge) -> None:
    """Filter s viacerými hodnotami (``?theme=A&theme=B``) príde celý, nie len prvá či posledná."""
    bridge.request(
        "POST",
        "/api/v1/auth/register",
        JSON,
        _body({"email": "ja@doma.sk", "password": "tajneheslo123", "accept_privacy": True}),
    )
    token = _json(bridge.request("POST", "/api/v1/auth/refresh", {}, None))["access_token"]
    auth = {**JSON, "authorization": f"Bearer {token}"}
    created = bridge.request(
        "POST", "/api/v1/catalog", auth, _body({"catalog_num": "10294", "theme": "Icons"})
    )
    assert created["status"] in (200, 201), _json(created)
    wished = bridge.request("POST", "/api/v1/wishlist", auth, _body({"catalog_num": "10294-1"}))
    assert wished["status"] == 201, _json(wished)

    def nums(query: str) -> list[str]:
        answer = bridge.request("GET", f"/api/v1/wishlist?{query}", auth, None)
        assert answer["status"] == 200, _json(answer)
        return [row["catalog_num"] for row in _json(answer)]

    # Sériu bez kľúča Rebrickable účet nemusí vidieť; potom je set „bez série“.
    own = "Icons" if nums("theme=Icons") else "__none__"
    assert nums("theme=Nic") == []
    assert nums(f"theme=Nic&theme={own}") == ["10294-1"]
    assert nums(f"theme={own}&theme=Nic") == ["10294-1"]
    themes = bridge.request("GET", f"/api/v1/wishlist/themes?theme={own}&theme=Nic", auth, None)
    assert themes["status"] == 200


def test_save_file_writes_what_the_dialog_chose(bridge: Bridge, tmp_path) -> None:
    target = tmp_path / "zbierka.csv"
    bridge.choose_save_path = lambda name: str(target)
    assert bridge.save_file("zbierka.csv", base64.b64encode(b"a;b\n").decode()) is True
    assert target.read_bytes() == b"a;b\n"
    bridge.choose_save_path = lambda name: None
    assert bridge.save_file("zbierka.csv", base64.b64encode(b"x").decode()) is False


def test_background_task_runs_after_the_answer() -> None:
    """Ako v uvicorne: odpoveď nečaká na úlohu z BackgroundTasks.

    Inak by obnova cien cez most vrátila 202 až po celej dávke a okno by
    stav „beží“ nevidelo; ďalšia požiadavka počas behu musí prejsť.
    """
    from fastapi import BackgroundTasks, FastAPI

    app = FastAPI()
    release = threading.Event()
    finished = threading.Event()

    async def slow() -> None:
        while not release.is_set():
            await asyncio.sleep(0.01)
        finished.set()

    @app.post("/start", status_code=202)
    async def start(background: BackgroundTasks) -> dict:
        background.add_task(slow)
        return {"running": True}

    @app.get("/status")
    async def status_() -> dict:
        return {"finished": finished.is_set()}

    @app.get("/boom")
    async def boom() -> dict:
        raise RuntimeError("chyba pred odpoveďou")

    started = Bridge(app, run_lifespan=False)
    try:
        answer = started.request("POST", "/start", {}, None)
        assert answer["status"] == 202
        assert _json(answer) == {"running": True}
        assert _json(started.request("GET", "/status", {}, None)) == {"finished": False}
        release.set()
        assert finished.wait(5)
        assert _json(started.request("GET", "/status", {}, None)) == {"finished": True}
        # Chyba pred odpoveďou okno dostane ako doteraz, most nespadne.
        assert started.request("GET", "/boom", {}, None)["status"] in (500, 599)
    finally:
        release.set()
        started.close()


def test_data_dir_creates_folders_and_keeps_one_secret(tmp_path) -> None:
    data = DataDir(tmp_path / "MojeKocky")
    first = data.secret()
    assert len(first) >= 48
    assert DataDir(tmp_path / "MojeKocky").secret() == first
    env = data.environment()
    assert env["DATABASE_URL"].endswith("/lego.db")
    assert (tmp_path / "MojeKocky" / "photos").is_dir()
    assert env["ALLOW_REGISTRATION"] == "false"


def test_second_instance_is_refused(tmp_path) -> None:
    data = DataDir(tmp_path / "MojeKocky")
    first = data.lock()
    assert first is not None
    assert DataDir(tmp_path / "MojeKocky").lock() is None
    first.release()
    again = data.lock()
    assert again is not None
    again.release()


@pytest.mark.skipif(sys.platform != "win32", reason="netstat -ano je z Windows")
def test_bridge_opens_no_listening_port(bridge: Bridge) -> None:
    bridge.request("GET", "/api/v1/health", {}, None)
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    mine = [
        line
        for line in out.splitlines()
        if "LISTENING" in line and line.split()[-1] == str(os.getpid())
    ]
    assert mine == []
