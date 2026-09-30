# Moje kocky Desktop: inštalácia pre Windows bez servera na porte

## Kontext

Webová verzia (repo `lego-app`) beží ako server FastAPI v Dockeri a otvára
sa v prehliadači. Používateľ chce tú istú appku ako bežnú inštaláciu
(`.exe`) pre Windows, **bez servera počúvajúceho na porte**, a v novom,
samostatnom repozitári. Webové repo sa nemení.

Rozhodnutia používateľa (2026-09-28):
- Prístup A: Python ostáva, okno volá appku priamo (bez portu).
- S prihlasovaním heslom.
- Nové repo `C:\Users\matisak\projekty\moje-kocky-desktop` ako **samostatná
  kópia** kódu; nové funkcie sa medzi repami prenášajú ručne.

Overené skúškou na zahodenie (pywebview 6.2, WebView2, Windows 11):
- stránka načítaná cez `file://` a proces nemá **žiadny port** v stave
  LISTENING (bez `file://` si pywebview potichu spustí vlastný server,
  treba `ALLOW_FILE_URLS` a URL `file:///…`);
- ES moduly, `localStorage`, `isSecureContext`, `navigator.mediaDevices`
  (kamera viditeľná), WebAssembly aj `fetch` súborov z disku fungujú;
- most JS → Python (`js_api`) prenesie 1 MB za ~170 ms.
- Neoverené: či WebView2 v pywebview ukáže žiadosť o povolenie kamery
  (overí sa vo Fáze 1 na skutočnej čítačke).

## Architektúra

```
┌ okno pywebview (WebView2) ─────────────┐
│ frontend (Vue) z file:///…/web/        │
│   api klient → window.pywebview.api    │──┐ volanie funkcie, nie sieť
└────────────────────────────────────────┘  │
┌ ten istý proces Python ─────────────────┐ │
│ Bridge.request(method, path, headers,   │◀┘
│                body_base64)             │
│   → httpx.ASGITransport → FastAPI app   │ (rovnako ako testy, bez siete)
│   → SQLite a fotky v %APPDATA%          │
└─────────────────────────────────────────┘
```

- **Jeden proces, žiadny port.** FastAPI appka sa nespúšťa cez uvicorn;
  požiadavky z okna idú cez `httpx.ASGITransport` priamo do nej, v
  samostatnom vlákne s vlastnou slučkou asyncio (`run_coroutine_threadsafe`).
  Celá logika backendu, migrácie a testy ostávajú.
- **Most** (`desktop/bridge.py`): jedna metóda `request` pre všetky
  volania API (telo aj odpoveď v base64, hlavičky ako slovník) a
  `save_file(name, data_base64)` s natívnym dialógom „Uložiť ako“
  (`create_file_dialog`) pre export CSV, ZIP a súpis.
- **Frontend**: api klient (`openapi-fetch`) dostane vlastný `fetch`, ktorý
  v desktope volá most namiesto siete. Všetko ostatné (obrazovky, stores)
  sa nemení. Router v režime `hash`, lebo `file://` nepozná cesty. Build
  s `base: './'`.
- **Údaje**: `%APPDATA%\MojeKocky\` → `lego.db`, `photos\`, `secret.key`
  (tajomstvo na šifrovanie kľúčov, vygeneruje sa pri prvom spustení,
  prístupné len používateľovi), `logs\`. Odinštalovanie údaje nemaže (voľba
  v inštalátore).
- **Jedna inštancia**: zámok v `%APPDATA%`; druhé spustenie len vytiahne
  okno do popredia.

## Prihlásenie

- Prvé spustenie: obrazovka „Vytvor si účet“ (meno, e-mail nepovinný,
  heslo). Ďalšie spustenia: heslo. Registrácia potom zatvorená (správca ju
  vie otvoriť pre ďalšieho člena domácnosti).
- Relácia žije, kým je okno otvorené: prístupový token v pamäti ako dnes.
  Obnovovacie cookie netreba (nie je prehliadač ani server); po zatvorení
  okna sa pri ďalšom spustení pýta heslo.
- Heslá, šifrovanie kľúčov a viditeľnosť podľa kľúča ostávajú bez zmeny.

## Čo sa oproti webu mení alebo vypne

| Vec | Desktop |
|---|---|
| Odkazy na pozretie (`/z/:token`) | vypnuté: bez servera ich nemá kto otvoriť |
| `/img` proxy | netreba, obrázky priamo z CDN (používa ich len vlastník počítača) |
| Cookies, CORS, rate limit, `index.html` bez kešu | netreba |
| Zásady ochrany súkromia | skrátené: údaje ostávajú na tomto počítači; služby ako na webe |
| Docker, `.env` | netreba; nastavenia v `%APPDATA%\MojeKocky\settings.json` |
| Sťahovanie súborov | natívny dialóg cez most |
| Obnova cien, import, skenovanie, Overiť cenu, galéria | rovnako |

## Balenie a inštalácia

- **PyInstaller** (onedir): Python, backend, závislosti a hotový frontend
  (`web/`) do `MojeKocky\`. Migrácie Alembic pribalené a spustené pri štarte.
- **Inno Setup**: inštalácia pre používateľa bez práv správcu
  (`%LOCALAPPDATA%\Programs\MojeKocky`), odkaz v ponuke Štart a na ploche,
  odinštalovanie, ikona, verzia.
- **WebView2**: vo Windows 10/11 býva; inštalátor ho overí a pri chýbajúcom
  spustí Evergreen bootstrapper od Microsoftu.
- **Veľkosť**: odhad 60–90 MB.
- **Podpis**: nepodpísané (SmartScreen raz upozorní). Podpisový certifikát
  je voliteľný neskôr.
- **Zostavenie**: GitHub Actions `windows-latest` pri tagu `v*`, výsledok
  `MojeKocky-Setup-x.y.z.exe` v Releases. Lokálne `scripts\build.ps1`.
- **Verzia**: jediný zdroj je `version` v `backend/pyproject.toml` (ako na
  webe). Inštalátor, `MojeKocky.exe` (Podrobnosti súboru,
  `packaging/version_info.py`) aj appka (Nastavenia → Aplikácia) hlásia to
  isté číslo; `build.ps1` inú verziu nezostaví, takže tag `v1.2.3` musí
  sedieť s `pyproject.toml`. PyInstaller pribaľuje metadáta balíka
  `lego-api`, inak by program hlásil `0+unknown`.
- **Záloha pri aktualizácii**: nová verzia sa inštaluje cez starú a pri
  prvom spustení (aj bez zmeny schémy) appka skopíruje databázu do
  `%APPDATA%\MojeKocky\backups` (posledných 5, `services/db_backup.py`, ako na
  webe). Keď záloha alebo migrácia zlyhá, okno so správou povie dôvod,
  prípadne kde je záloha a ako ju vrátiť (zmazať `lego.db-journal`, `-wal`,
  `-shm`, skopírovať zálohu na miesto `lego.db`, nainštalovať predchádzajúcu
  verziu); podrobnosti ostanú v `logs\moje-kocky.log`. Zálohu zo značky
  zlyhanej migrácie správa ukáže, len keď databáza je tá, ktorú zlyhaný
  štart nechal (revízia a odtlačok); po návrate zálohy a ďalšej práci by
  jej opätovný návrat zobral nové údaje.

## Fázy

1. **Kostra a most**: kópia kódu z `lego-app` (bez histórie), vstupný bod
   `desktop/main.py`, most, cesty do `%APPDATA%`, tajomstvo, jedna inštancia,
   frontend s mostom a hash routerom. Otvorí sa okno, prihlásenie a Zbierka
   fungujú, žiadny port. Overenie kamery.
2. **Úpravy pre desktop**: vypnúť zdieľanie a proxy, prvé spustenie
   (vytvorenie účtu), sťahovanie cez dialóg, skrátené zásady, nastavenia
   v `settings.json`.
3. **Balenie**: PyInstaller + Inno Setup, skript zostavenia, test inštalácie,
   spustenia, aktualizácie (nová verzia cez starú, údaje ostanú) a
   odinštalovania.
4. **GitHub Actions** a README desktopovej verzie.

## Testovanie

- Backend: celý súčasný test (pytest) beží ďalej.
- Nové testy mostu: `Bridge.request` vráti rovnakú odpoveď ako testovací
  klient (JSON, binárne, chyby 4xx), cesty a tajomstvo v dočasnom
  `%APPDATA%`, zámok jednej inštancie.
- Frontend: testy adaptéra `fetch` (požiadavka a odpoveď cez most, binárne
  telo, chyba), hash router.
- Kontrola „žiadny port“: test spustí most bez okna a overí, že proces
  nepočúva na žiadnom porte (netstat pre vlastný PID).
- Záloha pri aktualizácii a správa pri páde štartu (`test_desktop_backup.py`,
  vlastný `APPDATA` v dočasnom priečinku); zhoda verzie inštalátora, skriptu
  zostavenia a .exe s `pyproject.toml` (`test_desktop_version.py`).
- Ručne na čistom Windows (Fáza 3): inštalácia bez práv správcu, prvé
  spustenie, skenovanie čítačkou aj kamerou, obnova cien, export, aktualizácia,
  odinštalovanie.
