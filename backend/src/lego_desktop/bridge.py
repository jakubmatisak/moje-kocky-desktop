"""Most medzi oknom a appkou: volanie funkcie namiesto siete.

Okno (frontend) nevolá server na porte. Každú požiadavku API pošle cez
``window.pywebview.api.request`` sem a most ju odovzdá appke FastAPI
priamo, cez ``httpx.ASGITransport`` (rovnako to robia testy). Appka beží
v samostatnom vlákne s vlastnou slučkou asyncio; pywebview volá metódy
mosta z iných vlákien, preto ``run_coroutine_threadsafe``.

Klient httpx drží obnovovacie cookie prihlásenia, kým je okno otvorené.
Po zatvorení okna zmizne a pri ďalšom spustení sa pýta heslo, okrem
zapamätaného prihlásenia: trvalé cookie most uloží zašifrované
(``lego_desktop.remember``) a pri štarte ho klientovi vráti.
"""

import asyncio
import base64
import logging
import threading
from collections.abc import Callable
from http.cookiejar import Cookie
from pathlib import Path

import httpx

from lego_desktop.remember import REFRESH_COOKIE, RememberedLogin

log = logging.getLogger(__name__)

#: Dlhšie ako najdlhšia požiadavka (import veľkej zbierky, obnova ceny).
TIMEOUT_SECONDS = 600


def _sent_login(request: httpx.Request) -> str | None:
    """Obnovovacie cookie, s ktorým požiadavka odišla."""
    for part in request.headers.get("cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == REFRESH_COOKIE:
            return value
    return None


class Bridge:
    def __init__(
        self, app, run_lifespan: bool = True, remembered: RememberedLogin | None = None
    ) -> None:
        self._app = app
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://desktop",
            timeout=TIMEOUT_SECONDS,
        )
        self._stop: asyncio.Event | None = None
        self._lifespan_task = None
        #: Kam uložiť súbor; okno ho nahradí natívnym dialógom „Uložiť ako“.
        self.choose_save_path: Callable[[str], str | None] = lambda name: None
        self._remembered = remembered
        self._restore_login()
        if run_lifespan:
            self._start_lifespan()

    # --- zapamätané prihlásenie ------------------------------------------------

    def _restore_login(self) -> None:
        """Vráti klientovi zapamätané cookie; frontend sa cez /auth/refresh prihlási sám."""
        if self._remembered is None:
            return
        saved = self._remembered.load()
        if saved is not None:
            self._client.cookies.set(
                REFRESH_COOKIE, saved["value"], domain=saved["domain"], path=saved["path"]
            )

    def _current_login(self) -> Cookie | None:
        for cookie in self._client.cookies.jar:
            if cookie.name == REFRESH_COOKIE:
                return cookie
        return None

    def _keep_login(self, path: str, response: httpx.Response) -> None:
        """Súbor sleduje obnovovacie cookie zo servera.

        Trvalé cookie (zaškrtnuté Zapamätať si prihlásenie) sa uloží, pri
        každej obnove znova. Session cookie (prihlásenie bez zaškrtnutia,
        zmena hesla) a zmazané cookie (odhlásenie, zmazanie účtu) súbor
        zmažú, rovnako odmietnutá obnova. Tá sa neráta, keď odišlo staršie
        cookie, než aké klient drží: dve obnovy naraz (pywebview volá most
        z viacerých vlákien) by inak zmazali práve vydané prihlásenie.
        """
        if self._remembered is None:
            return
        sets_cookie = any(
            header.startswith(f"{REFRESH_COOKIE}=")
            for header in response.headers.get_list("set-cookie")
        )
        try:
            if sets_cookie:
                cookie = self._current_login()
                if cookie is not None and cookie.expires is not None:
                    self._remembered.save(cookie)
                else:
                    self._remembered.clear()
            elif response.status_code == 401 and httpx.URL(path).path.endswith("/auth/refresh"):
                current = self._current_login()
                if current is None or current.value == _sent_login(response.request):
                    self._remembered.clear()
        except OSError:
            # Prihlásenie v okne platí aj tak; len sa nezapamätá (alebo nezabudne).
            log.exception("Súbor so zapamätaným prihlásením sa nepodarilo zapísať")

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(TIMEOUT_SECONDS)

    def _start_lifespan(self) -> None:
        """Štart appky ako v uvicorne: migrácie databázy a jednorazové úlohy."""
        started = threading.Event()
        failure: list[BaseException] = []

        async def hold() -> None:
            self._stop = asyncio.Event()
            try:
                async with self._app.router.lifespan_context(self._app):
                    started.set()
                    await self._stop.wait()
            except BaseException as exc:  # noqa: BLE001 - odovzdá sa volajúcemu
                failure.append(exc)
                started.set()

        self._lifespan_task = asyncio.run_coroutine_threadsafe(hold(), self._loop)
        started.wait()
        if failure:
            raise failure[0]

    # --- volané z okna -------------------------------------------------------

    def request(self, method: str, path: str, headers: dict | None, body: str | None) -> dict:
        """Jedna požiadavka API. Telo aj odpoveď v base64 (aj binárne súbory)."""

        async def go() -> dict:
            content = base64.b64decode(body) if body else None
            response = await self._client.request(
                method, path, headers=headers or {}, content=content
            )
            self._keep_login(path, response)
            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": base64.b64encode(response.content).decode("ascii"),
            }

        try:
            return self._run(go())
        except Exception as exc:  # noqa: BLE001 - okno dostane chybu, nie pád
            log.exception("Požiadavka %s %s zlyhala", method, path)
            return {
                "status": 599,
                "headers": {},
                "body": base64.b64encode(str(exc).encode()).decode(),
            }

    def save_file(self, filename: str, data: str) -> bool:
        """Uloží súbor (export CSV, ZIP, šablóna) cez dialóg „Uložiť ako“."""
        target = self.choose_save_path(filename)
        if not target:
            return False
        Path(target).write_bytes(base64.b64decode(data))
        return True

    # --- koniec --------------------------------------------------------------

    def close(self) -> None:
        async def shutdown() -> None:
            await self._client.aclose()
            if self._stop is not None:
                self._stop.set()

        try:
            self._run(shutdown())
            if self._lifespan_task is not None:
                self._lifespan_task.result(30)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(5)
