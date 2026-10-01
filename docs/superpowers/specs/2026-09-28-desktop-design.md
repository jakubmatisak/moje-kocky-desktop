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
  Celá logika backendu, migrácie a testy ostávajú. `ASGITransport` by čakal
  aj na úlohy z `BackgroundTasks`; `bridge.py::answer_first` vráti odpoveď
  po poslednej časti tela a úloha dobehne v slučke mosta, ako v uvicorne
  (obnova cien hlási „beží“, import dohľadáva sety, kým okno čaká).
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
  prístupné len používateľovi), `logs\`. Odinštalovanie údaje nemaže, len
  keď to používateľ v otázke potvrdí (a len údaje účtu, pod ktorým beží;
  s heslom iného správcu nič).
- **Jedna inštancia**: zámok v `%APPDATA%`; druhé spustenie len vytiahne
  okno do popredia.

## Prihlásenie

- Prvé spustenie: obrazovka „Vytvor si účet“ (meno, e-mail nepovinný,
  heslo). Ďalšie spustenia: heslo. Registrácia potom zatvorená (správca ju
  vie otvoriť pre ďalšieho člena domácnosti).
- Relácia žije, kým je okno otvorené: prístupový token v pamäti ako dnes.
  Obnovovacie cookie drží most v klientovi httpx (okno cookie nemá); po
  zatvorení okna sa pri ďalšom spustení pýta heslo. Bez zapamätania platí
  na serveri najviac 12 hodín bez použitia, ako na webe.
- **Zapamätať si prihlásenie na tomto počítači** (políčko pri prihlásení
  ako na webe): server pošle trvalé cookie a most
  (`lego_desktop/bridge.py::_keep_login`) ho uloží zašifrované do
  `%APPDATA%\MojeKocky\session.bin` (`lego_desktop/remember.py`, Fernet
  odvodený zo `secret.key` ako pri kľúčoch k službám, žiadny nový kľúč),
  pri každej obnove znova. Pri štarte ho `_restore_login` vráti do klienta
  a frontend sa cez `/auth/refresh` prihlási sám. Súbor sleduje cookie zo
  servera: session cookie (bez zaškrtnutia) a zmazané cookie (odhlásenie,
  zmazanie účtu) ho zmažú, rovnako 401 pri obnove, no len keď odišlo
  cookie, ktoré klient drží. Zmena hesla v okne pošle nové trvalé cookie
  a súbor sa prepíše. Dve obnovy naraz z dvoch vlákien pywebview: neskoršia
  do ochrannej lehoty dostane len prístupový token bez Set-Cookie a súbor
  ostane; starý token po lehote server berie ako ukradnutý a zruší všetky
  prihlásenia účtu. Poškodený, vypršaný alebo iným tajomstvom zašifrovaný súbor
  sa ticho zmaže a appka sa pýta heslo. Do exportu nepatrí; odinštalovanie
  s mazaním údajov ho zmaže s priečinkom.
- Heslá, šifrovanie kľúčov a viditeľnosť podľa kľúča ostávajú bez zmeny.

## Čo sa oproti webu mení alebo vypne

| Vec | Desktop |
|---|---|
| Odkazy na pozretie (`/z/:token`) | vypnuté: bez servera ich nemá kto otvoriť |
| `/img` proxy | netreba, obrázky priamo z CDN (používa ich len vlastník počítača) |
| Cookies, CORS, rate limit, `index.html` bez kešu | netreba |
| Zásady ochrany súkromia | skrátené: údaje ostávajú na tomto počítači; služby ako na webe. Tabuľka úložiska okna uvádza namiesto cookie `lego_refresh` súbor `session.bin` (30 dní od posledného použitia, zmaže ho odhlásenie); okno cookies na sledovanie nepoužíva |
| Docker, `.env` | netreba; nastavenia v `%APPDATA%\MojeKocky\settings.json` |
| Sťahovanie súborov | natívny dialóg cez most |
| Obnova cien, import, skenovanie, Overiť cenu, galéria | rovnako |

## Balenie a inštalácia

- **PyInstaller** (onedir): Python, backend, závislosti a hotový frontend
  (`web/`) do `MojeKocky\`. Migrácie Alembic pribalené a spustené pri štarte.
- **Inno Setup**: od 1.0.0 inštalácia pre všetkých používateľov počítača
  (`PrivilegesRequired=admin`, bez voľby „len pre mňa“): inštalátor si
  vypýta práva správcu (Windows ukáže otázku UAC), program ide do
  `{autopf}\MojeKocky` (64-bitové Program Files), odkaz v ponuke Štart a na
  ploche pre všetkých (`{group}`, `{autodesktop}`), odinštalovanie, ikona,
  verzia, to isté AppId. Údaje má každý používateľ vlastné
  v `%APPDATA%\MojeKocky`; zakladá si ich appka, inštalátor na ne nesiaha.
  Appka po inštalácii beží pod účtom, ktorý inštalátor spustil
  (`runasoriginaluser`), inak by si údaje založila u správcu.
  Rozhodnutie používateľa (2026-09-30): „inštalátor si vypýta správcu sám“.
- **Prechod zo 0.1.x** (inštalácia len pre jedného používateľa
  v `%LOCALAPPDATA%\Programs\MojeKocky`, kľúč odinštalovania v HKCU):
  `PrepareToInstall` a `packaging/old-install.iss`. Starý odinštalátor sa
  nespúšťa, lebo sa pýta, či zmazať údaje. Priečinok z `InstallLocation`
  (bez kľúča predvolený, ak to nie je priečinok novej inštalácie) sa zmaže
  priamo, potom kľúč v HKCU a staré skratky (`{userprograms}\Moje kocky\*.lnk`,
  `{userdesktop}\Moje kocky.lnk`). Poistka: mazať sa smie len úplná cesta
  končiaca `\Programs\MojeKocky`, ktorá nie je v `{userappdata}` ani ho
  neobsahuje; iný priečinok inštalátor nemaže a povie, ako starú verziu
  odinštalovať. Najprv sa maže `MojeKocky.exe`: bežiaci program Windows
  zmazať nedovolí (premenovať priečinok áno, to preto nestačí) a vtedy
  inštalácia skončí s „Zavri Moje kocky a spusti inštaláciu znova.“ bez
  zmeny. Keď program nebeží, ale `DelTree` nezmaže všetko (súbor v
  `_internal` drží antivírus či konzola), hláška povie, že priečinok sa
  nepodarilo celý zmazať; kľúč v HKCU a skratky ostanú, aby opakovaná
  inštalácia starú inštaláciu našla a dokončila. Obmedzenie: HKCU a profil sú účtu, pod ktorým inštalátor po UAC
  beží. Pri zadaní hesla iného účtu správcu na bežnom účte, alebo keď mal
  0.1.x ďalší používateľ, jeho stará inštalácia ostane a odinštaluje si ju
  sám (údaje nechá). Návrat na 0.1.x: najprv odinštalovať 1.0.0.
- **Odinštalovanie** sa opýta, či zmazať aj údaje, predvolene Nie
  (`SuppressibleMsgBox`, aj v tichom režime s `/SUPPRESSMSGBOXES`), a zmaže
  len `{userappdata}\MojeKocky` účtu, pod ktorým beží; údaje ostatných
  používateľov ostanú. Otázka menuje účet Windows aj priečinok, nie „tvoje
  údaje“. Na bežnom účte s heslom iného správcu beží odinštalovanie pod
  týmto správcom a `{userappdata}` je jeho: keď sa účet procesu
  (`GetUserNameString`) líši od používateľa relácie Windows
  (`WTSQuerySessionInformationW`, `WTSUserName`), otázka sa nekladie, nemaže
  sa nič a hláška povie, že údaje toho, kto odinštaluje, ostali v jeho
  `%APPDATA%\MojeKocky` (`packaging/uninstall-data.iss`). Neznámy
  používateľ relácie sa neráta, otázka potom len menuje účet. Manifest inštalátora je aj s `admin` `asInvoker`,
  Inno Setup si práva vypýta sám hneď po spustení.
- **WebView2**: vo Windows 10/11 býva; inštalátor ho overí (HKLM aj HKCU)
  a pri chýbajúcom ponúkne stránku Microsoftu na stiahnutie. Otvára ju
  `ShellExecAsOriginalUser`, teda v prehliadači toho, kto inštalátor spustil,
  nie ako správca. HKCU je účtu, pod ktorým Setup beží: pri hesle iného
  správcu sa WebView2 nainštalovaný len pre bežného používateľa nenájde
  a inštalátor zbytočne ponúkne stiahnutie (zriedkavé, nerieši sa).
- **Jazyk inštalátora**: slovenčina a angličtina; Inno Setup ponúkne jazyk
  Windows a odinštalovanie ide v jazyku inštalácie. Všetky vlastné texty
  (otázka na WebView2, položka licencií v ponuke Štart, otázky
  odinštalovania, hlášky o starej inštalácii) sú v `packaging/messages.iss`
  ako `slovak.*` a `english.*`, skripty ich berú cez `CustomMessage` a
  `{cm:…}`. Okná so správou appky (pád štartu, „už bežia“) sú skôr, než
  appka pozná jazyk účtu, preto hovoria jazykom Windows
  (`GetUserDefaultUILanguage`: slovenčina, inak angličtina).
- **Veľkosť**: odhad 60–90 MB.
- **Podpis**: nepodpísané (SmartScreen raz upozorní). Podpisový certifikát
  je voliteľný neskôr.
- **Zostavenie**: GitHub Actions `windows-latest` pri tagu `v*`, výsledok
  `MojeKocky-Setup-x.y.z.exe` v Releases. Lokálne `scripts\build.ps1`.
- **Verzia**: jediný zdroj je `version` v `backend/pyproject.toml` (ako na
  webe). Inštalátor (aj v Podrobnostiach svojho súboru), `MojeKocky.exe`
  (Podrobnosti súboru, `packaging/version_info.py`) aj appka (Nastavenia →
  Aplikácia) hlásia to isté číslo; `build.ps1` inú verziu nezostaví, takže tag `v1.2.3` musí
  sedieť s `pyproject.toml`. PyInstaller pribaľuje metadáta balíka
  `lego-api`, inak by program hlásil `0+unknown`.
- **Záloha pri aktualizácii**: nová verzia sa inštaluje cez starú a pri
  prvom spustení (aj bez zmeny schémy) appka skopíruje databázu do
  `%APPDATA%\MojeKocky\backups` (posledných 5, najviac 90 dní,
  `services/db_backup.py`, ako na webe; príkaz `restore-backup` desktop
  neuvádza, návrat ide podľa okna). Keď záloha alebo migrácia zlyhá, okno
  so správou povie dôvod,
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
- Inštalátor (`test_installer.py`): práva správcu, Program Files, skratky
  pre všetkých, kompilácia celého skriptu cez ISCC. Logiku prechodu zo 0.1.x
  skúša testovací inštalátor, ktorý v `InitializeSetup` zavolá funkcie
  z `old-install.iss` s cestami v dočasnom priečinku a vymysleným kľúčom
  v HKCU a skončí (nič neinštaluje): poistka proti `%APPDATA%`, zmazanie
  programu a skratiek s údajmi netknutými, bežiaci program (kópia PING.EXE)
  nechá všetko tak.
- Ručne na čistom Windows (Fáza 3): inštalácia s otázkou UAC, aj na bežnom
  účte s heslom správcu, aktualizácia zo 0.1.x, prvé spustenie, skenovanie
  čítačkou aj kamerou, obnova cien, export, aktualizácia, odinštalovanie.
