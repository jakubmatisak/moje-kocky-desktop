"""Zapamätané prihlásenie desktopu: obnovovacie cookie v zašifrovanom súbore.

Okno cookie nemá, obnovovacie cookie drží most v klientovi httpx a so
zatvorením okna by zmizlo. Keď používateľ pri prihlásení zaškrtne
„Zapamätať si prihlásenie na tomto počítači“, server pošle trvalé cookie
(Max-Age 30 dní) a most ho uloží sem; session cookie (bez zaškrtnutia) sa
neukladá nikdy. Súbor je zašifrovaný tou istou šifrou ako kľúče k službám
(odvodenou zo ``secret.key``), takže samotný skopírovaný súbor nič neotvorí.
Poškodený, nečitateľný či vypršaný súbor sa ticho zmaže a appka sa pýta
heslo. Do exportu údajov nepatrí, je to prihlásenie, nie údaj zbierky.
"""

import json
import logging
import os
import time
from http.cookiejar import Cookie
from pathlib import Path

from lego_api.config import Settings
from lego_api.services import keys as keys_service

log = logging.getLogger(__name__)

#: Meno obnovovacieho cookie (``lego_api.auth.router.REFRESH_COOKIE``).
REFRESH_COOKIE = "lego_refresh"


class RememberedLogin:
    def __init__(self, path: Path, settings: Settings) -> None:
        self.path = Path(path)
        self._settings = settings

    def save(self, cookie: Cookie) -> None:
        """Uloží trvalé cookie; zápis cez dočasný súbor, aby nezostal napoly."""
        payload = json.dumps(
            {
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "expires": cookie.expires,
            }
        )
        token = keys_service.encrypt(payload, self._settings)
        partial = self.path.with_name(self.path.name + ".tmp")
        partial.write_text(token, encoding="ascii")
        os.replace(partial, self.path)

    def load(self) -> dict | None:
        """Uložené cookie (value, domain, path), alebo None.

        Čo sa nedá použiť (poškodené, iné tajomstvo, vypršané), sa zmaže:
        appka sa potom jednoducho opýta heslo.
        """
        try:
            text = self.path.read_bytes().decode("ascii").strip()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError):
            return self._discard()
        raw = keys_service.decrypt(text, self._settings)
        if raw is None:
            return self._discard()
        try:
            saved = json.loads(raw)
            value, domain, path = saved["value"], saved["domain"], saved["path"]
            expires = saved.get("expires")
        except (ValueError, TypeError, KeyError):
            return self._discard()
        if not all(isinstance(x, str) for x in (value, domain, path)) or not value:
            return self._discard()
        if not isinstance(expires, int) or expires <= time.time():
            return self._discard()
        return {"value": value, "domain": domain, "path": path}

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def _discard(self) -> None:
        log.info("Zapamätané prihlásenie sa nedá použiť, súbor sa zmaže")
        self.clear()
        return None
