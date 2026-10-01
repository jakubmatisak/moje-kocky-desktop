# Moje kocky Desktop — poznámky pre prácu v tomto repozitári

Desktopová verzia (Windows, inštalátor) webovej appky Moje kocky
(`github.com/jakubmatisak/moje-kocky-webapp`). **Samostatná kópia kódu**: zmeny sa
medzi repami prenášajú ručne. Spec desktopu:
`docs/superpowers/specs/2026-09-28-desktop-design.md`.

**Žiadny server na porte.** Okno pywebview (WebView2) načíta
`frontend/dist-desktop` cez `file://` (`ALLOW_FILE_URLS`, inak si pywebview
potichu spustí vlastný server) a volania API idú mostom
(`lego_desktop/bridge.py`, `window.pywebview.api.request`) priamo do FastAPI
cez `httpx.ASGITransport`. Frontend v režime `desktop`
(`import.meta.env.VITE_DESKTOP`): `src/desktop/bridge.ts` nahrádza fetch pre
adresy `https://moje-kocky.desktop/…`, router je `hash`, súbory sa ukladajú
cez `utils/saveBlob.ts` (dialóg „Uložiť ako“), obrázky priamo bez `/img`,
zdieľanie odkazom je skryté. Klient API hľadá `fetch` až pri volaní, inak
by si zapamätal pôvodný a prvé volanie by sa zaseklo.
`ASGITransport` čaká, kým appka skončí celá, aj s úlohami z
`BackgroundTasks`; most ho preto obaľuje `bridge.py::answer_first`: odpoveď
sa vráti po poslednej časti tela a úloha dobehne v slučke mosta ako
v uvicorne. Bez toho by 202 z obnovy cien prišla až po celej dávke a okno
by stav „beží“ nevidelo (`test_background_task_runs_after_the_answer`).

**Údaje v `%APPDATA%\MojeKocky`** (`lego_desktop/paths.py`): databáza,
fotky, `secret.key` (vznikne pri prvom spustení), zapamätané prihlásenie
(`session.bin`, len keď si ho používateľ zvolí), denníky, zálohy databázy
pred aktualizáciou (`backups\`, vedľa databázy podľa absolútnej
`DATABASE_URL`); zámok proti druhému spusteniu. Kamera sa pre `file://`
povolí bez pýtania (`_allow_camera` v `lego_desktop/main.py`).

**Zapamätané prihlásenie je `session.bin`.** Okno cookie nemá, obnovovacie
cookie drží most. Trvalé cookie (zaškrtnuté „Zapamätať si prihlásenie na
tomto počítači“) uloží `bridge.py::_keep_login` zašifrované cez
`lego_desktop/remember.py` (Fernet zo `secret.key`, tá istá šifra ako
kľúče, `keys_service.encrypt`) a `_restore_login` ho pri štarte vráti
klientovi, takže frontend sa cez `/auth/refresh` prihlási sám. Session
cookie sa neukladá. Súbor zmaže každé session alebo zmazané cookie zo
servera (prihlásenie bez zaškrtnutia, odhlásenie, zmazanie účtu) a 401 pri
obnove, ak odišlo cookie, ktoré klient práve drží. Zmena hesla v okne
zapamätanie nechá: server pošle nové trvalé cookie a súbor sa prepíše. Dve
obnovy naraz (pywebview volá most z viacerých vlákien) pošlú to isté
cookie; neskoršia do ochrannej lehoty (`refresh_grace_seconds`) dostane
200 bez Set-Cookie a súbor ostane. Obnova so starým cookie po lehote je
ukradnuté cookie, server zruší všetky prihlásenia účtu a 401 súbor zmaže.
Poškodený či cudzím tajomstvom zašifrovaný súbor
sa ticho zmaže. Zápis cez dočasný súbor; chyba zápisu požiadavku nezhodí.
Zásady to opisujú v `SK_DESKTOP`/`EN_DESKTOP`. Testy v
`tests/test_desktop_remember.py` s priečinkom v `tmp_path`.

**Pád pri štarte ukáže okno so správou**, denník používateľ nevidí.
`lego_desktop/main.py::startup_failure_text`: pri `BackupFailed` jej text
(databáza ostala bez zmeny), pri spadnutej migrácii záloha zo značky
`backups/lego-failed-migration.json` a ako ju vrátiť, inak cesta k denníku.
Značke verí, len keď revízia a odtlačok sedia na databázu (tá istá kontrola
ako `db_backup._earlier_backup`): po návrate zálohy a práci v starej verzii
by rada vrátiť ju znova zobrala všetko zadané odvtedy.
Testy v `tests/test_desktop_backup.py` majú vlastný `APPDATA` v `tmp_path`.
Okná so správou (pád štartu, „už bežia“) sú skôr, než appka pozná jazyk
účtu, preto hovoria jazykom Windows: `ui_language` (primárny jazyk
`GetUserDefaultUILanguage` 0x1B = slovenčina, inak angličtina; mimo Windows
a bez odpovede slovenčina), texty v `_TEXTS`. Text `BackupFailed` je
slovenský zo zdieľaného kódu, anglická správa povie to isté sama a z výnimky
vezme len `__cause__`. Testy záloh si jazyk pripnú na slovenčinu
(`slovak_windows`), anglické ho dávajú výslovne (`lang="en"`).

**Balenie:** `scripts/build.ps1` → `npm run build-desktop` → PyInstaller
(`packaging/moje-kocky.spec`; migrácie a ich importy musia byť v spec, lebo
sa načítavajú zo súborov) → Inno Setup (`packaging/moje-kocky.iss`).
GitHub Actions `release` pri tagu `v*`. Spec pribaľuje metadáta balíka
`lego-api` (`copy_metadata`), inak by zabalený program hlásil `0+unknown`
a pri aktualizácii bez migrácie nezálohoval; verziu do .exe zapíše
`packaging/version_info.py`. Tie isté čísla dostane aj súbor inštalátora
(`VersionInfoVersion` z `/DAppFileVersion`, ktoré `build.ps1` vezme
z `version_info.py`; Inno Setup berie len čísla, text s príveskom ide
zvlášť), inak by hlásil 0.0.0.0. Verzia inštalátora je verzia appky:
`build.ps1` inú nepustí (tag `v1.2.3` = `version` v `pyproject.toml`),
predvolené čísla v `build.ps1` a `moje-kocky.iss` stráži
`tests/test_desktop_version.py`. Každé vydanie zvýši verziu.

**Inštalátor je pre všetkých, údaje sú každého používateľa.**
`PrivilegesRequired=admin` bez `PrivilegesRequiredOverridesAllowed`,
`{autopf}\MojeKocky`, skratky `{group}` a `{autodesktop}`, to isté AppId.
Sekcie mimo `[Code]` nesmú siahať na `{user…}` ani HKCU (údaje si zakladá
appka); appka po inštalácii beží `runasoriginaluser`, inak by si údaje
založila u správcu. Manifest je aj tak `asInvoker`, práva si Inno Setup
vypýta sám po spustení. Staršiu inštaláciu 0.1.x (`%LOCALAPPDATA%\Programs\MojeKocky`,
kľúč `…\Uninstall\{AppId}_is1` v HKCU) odstráni `PrepareToInstall` cez
`packaging/old-install.iss`, bez starého odinštalátora (pýta sa na údaje).
Poistka `IsOldProgramDir`: len úplná cesta končiaca `\Programs\MojeKocky`
mimo `{userappdata}`; iný priečinok nemaže a povie, ako odinštalovať.
Najprv ide `MojeKocky.exe`: bežiaci program Windows zmazať nedovolí
(premenovať priečinok áno, to nestačí) a inštalácia skončí s „Zavri Moje
kocky a spusti inštaláciu znova.“ bez zmeny. Keď potom `DelTree` nezmaže
všetko (súbor drží iný proces), program je preč a hláška je iná („sa
nepodarilo celý zmazať“, `OldDirLeftovers`); kľúč a skratky ostanú, aby
opakovaná inštalácia starú inštaláciu našla a dokončila. HKCU a profil sú
účtu, pod ktorým inštalátor po UAC beží; stará inštalácia iného účtu ostane
(zdokumentované v README). Aj preto stránku WebView2 otvára
`ShellExecAsOriginalUser`, nie `ShellExec` (prehliadač by bežal ako správca).
Odinštalovanie zmaže len `{userappdata}\MojeKocky` účtu, pod ktorým po UAC
beží, a len po otázke s menom toho účtu a predvolenou odpoveďou Nie
(`SuppressibleMsgBox`). Keď to nie je používateľ relácie Windows (bežný
účet s heslom iného správcu: `uninstall-data.iss`, `SessionUserName` cez
`WTSQuerySessionInformationW`, `OtherAccountElevated`), nepýta sa a nemaže
nič, len povie, kde údaje ostali. Nikde „tvoje údaje“: nemusia byť.
Funkcie v `old-install.iss` a `uninstall-data.iss` berú všetko ako
parametre: `tests/test_installer.py` ich skúša testovacím inštalátorom,
ktorý skončí v `InitializeSetup`, na dočasných priečinkoch a vymyslenom
kľúči. Skutočné cesty ani kľúč do testu nepatria. Komentáre v `[Code]` sú
`//`, lebo komentár v zložených zátvorkách skončí pri prvej konštante ako
`{app}`. Všetky štyri skripty sú v UTF-8 s BOM.
Texty pre používateľa (otázka na WebView2, položka licencií v ponuke Štart,
otázky odinštalovania, hlášky o starej inštalácii) sú len v
`packaging/messages.iss` ako `slovak.Meno` a `english.Meno`; skripty ich
berú cez `CustomMessage('Meno')`, s argumentmi `FmtMessage(…, [..])`, v
sekciách `{cm:Meno}`. `%n` zmení ISCC na nový riadok. Test stráži, že každá
hláška je v oboch jazykoch a že v skriptoch mimo `Log(…)` nie je reťazec
s diakritikou; testovací inštalátor beží s `/LANG=slovak` alebo `english`.

Nižšie sú pravidlá appky prevzaté z webového repa; platia aj tu, okrem
Dockeru, portu 8000 a zdieľania odkazom.

## Príkazy

```bash
# Backend
cd backend && uv run uvicorn lego_api.main:app --reload --port 8000
cd backend && uv run pytest
cd backend && uv run ruff check src tests && uv run ruff format src tests

# Frontend
cd frontend && npm run dev
cd frontend && npm run type-check && npm run lint && npm test
cd frontend && npm run build-only

# Po zmene API najprv export schémy, potom generovanie typov
cd backend && uv run python -m lego_api.openapi_export
cd frontend && npm run gen:api

# Migrácia po zmene modelu
cd backend && uv run alembic revision --autogenerate -m "popis"
```

## Pravidlá, ktoré sa ľahko porušia

**Kým účet nezadá kľúč, zo služby nevidí nič.** Spec
`2026-09-28-licencne-cista-architektura-design.md`. Údaj sa ukladá raz,
viditeľnosť rieši `lego_api/visibility.py` (ContextVar na požiadavku):
- Rebrickable: stačí mať vlastný kľúč (spoločné `catalog_items`, stĺpce
  `base_*`). Bez neho `name` = „Set {číslo}“, séria, fotka a členovia
  prázdni.
- Brickset a BrickEconomy: `brickset_facts`, `brickeconomy_facts` a snímky
  cien vidí účet, len keď odtlačok jeho kľúča má riadok v `source_access`
  (zapisuje `services/access.py::record` pri každom volaní). Ceny len do
  `last_fetched_at` vlastného volania.
- Ručné ceny majú `user_id`. UPCitemdb a Eurostat sú predvolene vypnuté
  (`CapSpec.default_enabled`, `FetchPolicy.enabled_caps`).

Požiadavka HTTP začína s `nothing()` (middleware v `main.py`), prihlásenie
nastaví stav účtu (`auth/deps.py`), verejný odkaz `public_visibility`. Kód
mimo požiadavky vidí všetko (`INTERNAL`). Atribúty `CatalogItem` (`name`,
`description`, `forecast_2y_eur`…) skladajú viditeľnú hodnotu. **Zápis
do katalógu ide cez `base_*`, facts cez `facts_for()`, nikdy „prečítam
viditeľnú hodnotu a zapíšem späť“**: v obmedzenom kontexte by to zmazalo
cudzie údaje. Nový zdroj s osobnou licenciou = vlastné facts, prístup
a vlastnosť na `CatalogItem`. `auth_client` v testoch vidí všetko,
pravidlá overuje `tests/test_visibility.py` s obyčajným `client`.

**Nerealizovaný a realizovaný zisk sa nikdy nesčítavajú.** Nerealizovaný je
`trhová hodnota − kúpna cena` cez položky so `status=owned`. Realizovaný je
čistý: `predajná − poplatky − poštovné − kúpna` cez `status=sold`
(`ValuedItem.realized`). Aj krivka výnosu v grafe je čistá. Do trhovej
hodnoty portfólia vstupujú len vlastnené kusy.

**Ročný výnos sa pod rok držania nepočíta.** `portfolio.annualized` vráti
None, lebo z +10 % za mesiac by vyšlo +214 % ročne. Skupina (téma, zoznam,
celá zbierka) je jeden celok s dobou držania váženou vkladom
(`collection_cagr`), nie priemer percent jednotlivých kusov.

**Odhad hodnoty platí len pre kusy v krabici.** BrickEconomy odhaduje nový
set. `_apply_forecast` berie len `new_sealed` kusy s odhadom a vedľa neho
dnešnú hodnotu tých istých kusov, aby sa rast dal porovnať.

**GDPR je v appke, nie v dokumente.** Zásady `/sukromie`
(`views/PrivacyView.vue`, prevádzkovateľ v `app_settings` → `operator`),
registrácia vyžaduje `accept_privacy` a ukladá `privacy_version`; po zmene
textu zvýš `settings.privacy_version`, používateľ uvidí oznámenie. Desktop
má v zásadách vlastné sekcie, preto jeho verzia môže byť vyššia než na webe
(2026-09-30.3: odinštalovanie s heslom iného správcu; 2026-09-30.4:
zapamätané prihlásenie; 2026-09-30.5: tabuľka úložiska okna má namiesto
cookie `lego_refresh` riadok `session.bin` a úvod netvrdí, že appka cookies
nepoužíva, len že okno ich na sledovanie nepoužíva); pri prenose `config.py`
z webu ju nezníž (stráži `tests/test_install_texts.py`).
`services/account.py` maže účet výslovne po tabuľkách aj so súbormi fotiek
(SQLite nemá zapnuté `foreign_keys`) a exportuje ZIP bez kľúčov. Nová
tabuľka s `user_id` = pridať ju do `_OWNED` a do exportu. Obrázky zo
služieb idú cez `GET /img` (`routers/images.py`, len povolení hostitelia)
a vo frontende cez `utils/imageSrc.ts`. Nové cookie alebo úložisko v
prehliadači = riadok v tabuľke na `/sukromie`; analytika či sledovanie =
najprv lišta so súhlasom. Nová kópia údajov mimo databázy (zálohy pred
aktualizáciou v `backups/`) = veta v zásadách aj s tým, ako dlho ostane.

**Vlastná fotka sa ukladá zmenšená, najviac 1 MB.**
`services/photo_processing.py::normalize`: Pillow ju prečíta (to je aj
kontrola, že ide o obrázok), otočí podľa EXIF, zmenší na 1600 px, uloží
JPEG bez metadát (preč je aj poloha GPS) a znižuje kvalitu, kým nie je
pod `photo_stored_max_bytes`. Vstup najviac `photo_max_bytes` (20 MB).
Staršie fotky zmenší `python -m lego_api.cli recompress-photos`.

**Fotky ležia na disku, v databáze je len ich popis.** Priečinok je
`PHOTOS_DIR`; v kontajneri `/app/data/photos`, teda na zväzku. Pracovný
priečinok kontajnera je `/app/backend`, relatívna cesta by fotky uložila
mimo zväzku a nasadenie by ich zmazalo. Typ súboru sa overuje podľa obsahu,
meno si vymýšľa server a so zmazaným kusom sa mažú aj súbory. `data/photos/`
je v `.gitignore`, fotky sú osobné.

**Každá aktualizácia appky dostane najprv zálohu.** Používateľ appku
aktualizuje sám a databáza sa zmigruje pri štarte; pokazená migrácia alebo
nová verzia kódu by bez kópie zobrala celú zbierku. `main.py::_migrate` ide
cez `services/db_backup.py::upgrade_with_backup`: keď revízia v
`alembic_version` nie je head, alebo nad databázou naposledy bežala iná
verzia appky (aj staršia), zálohovacie API SQLite (konzistentné aj pri
otvorenom spojení) skopíruje databázu do `backups/` vedľa nej
(`lego-RRRRMMDD-HHMMSS-v<verzia>-<revízia>.db`, stav pred štartom;
v kontajneri `/app/data/backups`, v desktope `%APPDATA%\MojeKocky\backups`).
Verzia je `lego_api.__version__`
(metadáta balíka, teda `pyproject.toml`, žiadna ručná kópia) a po úspešnej
migrácii sa zapíše do `app_settings` → `app_version` (`record_version`).
Pred migráciou ju `recorded_version` číta surovým SQL, lebo schéma môže
byť hocijaká stará; chýbajúca tabuľka či nečitateľná hodnota = verzia
neznáma = záloha (staršie inštalácie, v mene len revízia). Nová databáza,
pamäť ani head s tou istou verziou sa nezálohujú. Keď záloha zlyhá,
migrácia sa nespustí (`BackupFailed`). Staré zálohy maže `prune` (ostane
`KEEP` 5 a žiadna staršia než `MAX_AGE_DAYS` 90 podľa času v mene, so
zálohou aj jej `-journal`/`-wal`/`-shm`, iné súbory v priečinku nie) po
každom úspešnom štarte, aj bez novej zálohy; záloha tohto štartu a záloha
zo značky, ktorá ostala, vek nepozerajú. Po zlyhanom štarte sa nemaže
nič: SQLite potvrdzuje každú migráciu zvlášť, takže po páde je databáza napoly zmigrovaná a Docker
(`restart`) či ďalšie spustenie desktopu by inak rotáciou vytlačili
jedinú zálohu spred aktualizácie. Zlyhanie si pamätá
`backups/lego-failed-migration.json` (záloha, revízia, odtlačok databázy);
kým sa databáza odvtedy nezmenila, ďalší štart novú zálohu nerobí a hlási
tú pôvodnú. Každý úspešný štart značku zmaže, aj bez zálohy (vrátená
záloha a predchádzajúca verzia). Verzia sa pri páde nezapíše, takže to
platí aj pre štart novej verzie bez migrácie. Nové vydanie = zvýšiť `version` v `pyproject.toml`,
`uv lock` a verziu vo `frontend/package.json` aj `package-lock.json`
(zhodu stráži `tests/test_version.py`; v desktope aj predvolenú verziu
v `build.ps1` a `moje-kocky.iss`, `tests/test_desktop_version.py`), inak sa
pri aktualizácii bez migrácie nezálohuje. Verziu hlási `/health`, OpenAPI
a Nastavenia → Aplikácia (`components/AppVersion.vue`, v desktope bez
prevádzkovateľa, verzia ostáva). Log pri páde povie, kde je záloha,
príkaz na návrat `python -m lego_api.cli restore-backup <záloha>` (v Dockeri
cez `docker compose run --rm app`) a ručný postup: pred skopírovaním zálohy
treba zmazať `lego.db-journal` (`-wal`, `-shm`), inak ho SQLite vráti do
obnoveného súboru. Príkaz (`db_backup.restore_backup`) odmietne súbor bez
`integrity_check` ok a bez `alembic_version`, doterajšiu databázu aj so
žurnálom nemaže, ale presunie do `backups/` ako
`lego-RRRRMMDD-HHMMSS-pred-obnovou.db` (tvar zálohy, takže ju rotácia aj
vek zmažú ako zálohu; zásady to spomínajú), zálohu skopíruje zálohovacím
API a pri chybe všetko vráti. V desktope je príkaz len v kóde zdieľanom
s webom: README ho neuvádza a používateľ ide podľa okna pri páde štartu
(ručný postup), zásady desktopu odloženú databázu nespomínajú. Aby sa to do logu dostalo, `_migrate` nastaví
`config.attributes["keep_logging"]` a `alembic/env.py` potom nevolá
`fileConfig`, ktorý by vypol loggery appky aj uvicornu. Fotky záloha
nenesie. Zálohy obsahujú aj údaje neskôr zmazaných účtov, preto to
spomínajú zásady `/sukromie` (Ako dlho, Vymazanie: najdlhšie do prvého
štartu po 90 dňoch; v desktope `SK_DESKTOP` a `EN_DESKTOP` v sekciách Čo
appka ukladá a Tvoja kontrola); zmena `KEEP` či `MAX_AGE_DAYS` = text zásad
a `privacy_version`. `data/backups/` je v `.gitignore`.

**Bez trhovej ceny sa nezobrazuje nula.** Keď `price_source == "missing"`,
rozhranie ukáže pomlčku alebo „cena neznáma“, nie `0 €` a `−100 %`.
Platí to na karte setu, v detaile aj v zozname kusov. Aj súčty po skupinách:
keď cenu nemá ani jeden vlastnený kus, `market_value` a `unrealized` sú
null (Výkonnosť, `/stats/summary`, `FacetsOut.totals`), skupina bez ceny je
vo Výkonnosti na konci a Najväčší zisk kusy bez ceny vynechá (prázdna
karta to povie). Rovnako verejný odkaz (`market_total`/`market_value` null,
`price_missing`; verejnosť ceny BrickEconomy nevidí, takže bez ručnej ceny
je to bežné), súčet v Súpise, prázdna bunka hodnoty a nerealizovaného zisku
v exporte CSV a prázdne pole ceny v dialógu predaja. Reťazec `"0.00"` je
v JS pravdivý, na null sa testuje výslovne.

**Voľba položky na cenenie je na jednom mieste.** `services/pricing.py::resolve_price_target`.
Zdroj pozná dve podoby: set (`/api/v1/set/{num}`) a samotnú figúrku
(`/api/v1/minifig/{num}`). Zatvorený sáčok ani komplet so stojanom vlastné
číslo nemajú, cenia sa pod katalógovým číslom ako set. Holá figúrka sa cení
pod `minifig_no`, a keď ho nepoznáme, spadne to na set: volanie s katalógovým
číslom by skončilo chybou a zbytočne ukrojilo z kvóty. Či sa na cieľ vôbec
volá, rozhoduje `pricing.source_prices`: figúrka z Rebrickable mimo série
(`fig-…`, `is_bare_figure`) ako set nie, Overiť cenu ju necení a dávka ju
do plánu nedá. Nič z toho nepatrí do routera ani do komponentu.

**Jedno volanie na položku, nikdy viac.** Denná kvóta je 100 volaní.
Odpoveď nesie cenu novej aj použitej položky a k tomu históriu, takže sa
dávka delí podľa `PriceTarget.call_key()` (číslo a druh), nie podľa stavu.
Poistky sú v `services/refresh.py`, počítadlo kvóty v
`providers/brickeconomy.py`. Pri pridávaní čohokoľvek, čo siaha na ceny,
najprv zrátaj, koľko to stojí volaní za deň.

**História sa ukladá raz.** `store_market` zapisuje udalosti z
`price_events_*` pod ich vlastným dátumom (poludnie UTC) a preskočí tie,
ktoré už v databáze sú. Aktuálna hodnota sa naopak zapisuje vždy, aj keď sa
nezmenila: je to zároveň stopa, že sme sa dnes pýtali, a bez nej by prestala
fungovať poistka na vek snímky.

**Odpoveď o cene nesie aj metadáta.** `apply_catalog_extras` z nej doplní
odporúčanú cenu v eurách, stav retired a číslo figúrky a prepíše odhad
hodnoty o 2 a 5 rokov a rast za 12 mesiacov. Nestojí to ďalšie volanie,
len sa to nesmie zabudnúť uložiť. Rast môže byť záporný, preto sa nečíta
cez `_decimal`, ktoré zahadzuje nulu a mínus ako neplatnú cenu.

**Hromadná obnova raz za týždeň, ručná hneď.** `price_max_age_hours` je 168.
`POST /prices/refresh-all?num=` je ručná obnova z detailu a vek snímky
nepozerá (`force`); strop dávky a zvyšok kvóty platia aj pre ňu.
Hromadná obnova z hornej lišty ide cez dialóg `RefreshPricesDialog.vue`
(„Chcete obnoviť ceny?“, počet predvolene 50, najviac zvyšok dňa) a posiela
`?limit=`, ktorý nahradí predvolený strop `price_refresh_budget`; zvyšok
kvóty, rezerva a `price_batch` účtu platia ďalej. Riadok „Dnes použité X
z 90“ berie `calls_used`/`calls_limit` z `refresh-status`, rátané tou istou
`routers/usage.py::brickeconomy_used` ako karta limitov.
Vek je čas od posledného volania vlastného kľúča, s cenou aj bez nej
(`pricing.last_attempts`: `source_access` čísla a `miss:{číslo}`, k tomu
`price_misses`), alebo od novšej ručnej ceny. Poradie v `collect_targets`:
najprv neznáme, teda kľúč sa ešte nepýtal a cena chýba (Zbierka pred Chcem,
naposledy pridané prvé), potom ostatné od najstaršieho volania. Keď zdroj
odpovie, že cenu nemá (400/404 alebo odpoveď bez ceny), `store_miss` zapíše
`miss:{číslo}`, nie číslo samo, lebo to by odomklo cudzie ceny; rovnako
obnova jednej položky (`POST /prices/{num}/refresh`). Bez tejto
stopy by bola položka pri každom kliknutí neznáma, prvá a stála by volanie;
rovnako postavený kus setu v predaji, ktorému použitá cena nepríde nikdy.
Výpadok (`provider.last_answered` je False) sa nezapíše, skúsi sa nabudúce.
Pamäť `price_misses` sa v desktope stratí s každým zatvorením programu,
preto je stopa v databáze.

**Zberateľské série majú na Rebrickable nečakanú štruktúru.** Séria nie je
jeden set s dvanástimi figúrkami. Každá figúrka je samostatný set
(`71046-1` až `71046-12`) a drží ich pokope téma, ktorej nadradená téma je
„Collectible Minifigures“. Appka si nad nimi vyrobí zastrešujúcu položku
s holým číslom `71046`. Členovia sa ťahajú jedným volaním cez tému
(`/sets/?theme_id=`), nie cez `/sets/{num}/minifigs/`. Balenia v téme, teda
sáčok, kompletná sada a multipack, majú nula dielikov a medzi členov nepatria.

**Set nevracia názov témy, len `theme_id`.** Musí sa dotiahnuť cez
`/themes/{id}/`, inak zostane téma prázdna a rozpadne sa filter aj koláč.
Témy sa cachujú v pamäti procesu.

**Pri holom čísle má séria prednosť pred svojím prvým členom.**
`normalize_num` skúša variant `-1` ako prvý, takže bez poistky v `get_local`
by `71046` vrátilo jednu figúrku namiesto výberu z dvanástich.

**Sekcia Figúrky pozná všetky série, aj nezačaté.** Zoznam tém príde
jedným volaním Rebrickable (`/themes/?page_size=1000`), figúrky každej série
ďalším, lebo dotaz na nadradenú tému deti nevráti. Sťahuje sa na pozadí
(`services/cmf.py`), sekundu od seba, a séria sa ukladá cez
`CatalogService.store_series`, rovnako ako pri pridaní holého čísla. Číslo
série je to, ktoré sa medzi figúrkami opakuje. Nové série pribúdajú samy:
otvorenie sekcie raz za týždeň skontroluje zoznam, séria z tohto a minulého
roka sa raz za dva týždne stiahne znova. Zoznam tém je pomalý, preto tieto
dve volania majú dlhší limit než 10 s. Cenovú kvótu to nemíňa.

**Figúrky majú kategórie: minifigúrky a blind-box série iných radov.**
Mighty Machines, Super Mario Character Pack, VIDIYO, Unikitty!, Duplo vrecúška
nemajú vlastnú tému (Mighty Machines je medzi 460 setmi Technicu), preto sa
nájdu podľa balenia (`find_blind_series`: hľadanie „Random Box“ a pod.)
a figúrky sú varianty čísla (`42233-1` až `-8`). Balenie sa spozná aj podľa
názvu, nielen podľa nula dielikov: kompletná sada má niekedy dieliky všetkých
kusov. Ukladajú sa do `blind_series` s kategóriou; členovia sú `kind=set`,
cenia sa ako sety. Minifigúrky ostávajú v `cmf_series`, oddelene.

**„Kúpil som“ je jeden dialóg pre všetko, z Chcem vyraďuje server.**
`components/PurchaseDialog.vue` pridá do zbierky vec, ktorú katalóg už
pozná, z Chcem aj z chýbajúcej figúrky; Chcem sám nemaže. Kúpené vyradí
server pri každom pridaní: `services/wishlist.py::drop_bought` v tej istej
transakcii volajú `POST /items`, `/items/bulk`, import (Pridať set
číslom aj skenom, Mám ju, Mám všetky, ďalší kus) aj určenie figúrky
z rozbaleného sáčku (`PATCH /items/{id}/identify`). Porovnáva katalógové
číslo: figúrka vyradí seba, sáčok pod holým číslom sériu; vlastnený aj
rezervovaný kus áno, predaný nie. Pôvodnú položku nesie
`removed_from_wishlist` na prvom kuse setu (viac kusov vyradí raz) a Späť
ju vráti cez `POST /wishlist` aj s `created_at`
(`composables/useWishlistReturn.ts`). Pridať set ukáže po tlačidle
samostatné „Odstránené z Chcem“ so Späť len pre Chcem, po automatickom
uložení zo skenu jedno oznámenie a jedno Späť pre kusy aj Chcem. To vracia
Chcem až po zmazaní kusov a s `?unless_owned=true`: set, ktorý účet ešte
má (pri skenoch X, Y, X druhý kus X), server nevráti a odpovie 204
(`still_bought`, to isté pravidlo ako `drop_bought`). Import Chcem
z importov nechá (`keep_imported`, aj zo staršieho importu; náhľad sľubuje
vyradenie len pri ostatných a pri týchto povie, že ostanú) a vyradené si
pamätá na vrátenie, aj s dátumom pridania (`added_at`). Stránka Chcem
po pridaní či odobratí obnoví aj súhrn (odznak v ponuke) a zoznam načíta
raz (`WishlistView.vue::afterChange`); po kúpe ho načíta watch nad
`wishlist_count`, nie `@saved` dialógu, inak by šiel dvakrát.

**Katalógové vzťahy sa načítavajú výslovným dotazom.** `CatalogItem` zámerne
nemá ORM vzťah na členov série. Lenivé načítanie v asynchrónnej session padne
až pri serializácii, čo je ťažko dohľadateľné. Členov vracia
`CatalogService.members_of`, DTO sa skladá ručne v routeri.

**Sumy chodia z API ako reťazec s dvomi desatinnými miestami.** Typ `Money`
v `schemas/__init__.py` zaokrúhľuje na centy. Snímky sa ukladajú na štyri
desatinné miesta, kúpne ceny majú dve, bez zjednotenia by klient dostal raz
`1890.0000` a raz `1180.00`.

**Filtre zoznamu sú na jednom mieste.** `services/filters.py` používa
zoznam kusov, zoskupený zoznam aj počty v paneli (`/items/facets`). Kým to
boli dve kópie, zoskupený zoznam ticho ignoroval hľadanie aj čipy
a používateľ videl celú zbierku bez ohľadu na to, čo nastavil. Nový filter
je jeden záznam v `ItemFilter`, jeden predikát v `PREDICATES` a jedna
skupina vo `facets()`, nie podmienka v routeri. Vo frontende jeden
záznam v zoznamoch polí `stores/filters.ts` (zoznam, číslo, dátum,
prepínač) a popis v `composables/useFilterLabels.ts`. Hľadanie ignoruje
diakritiku (`filters.fold`), každé slovo musí sedieť.

**Zbierka sú len sety, figúrky zo sérií sú vo Figúrkach.** Zbierka posiela
`sets_only=true` (`filterStore.sectionQuery()` v zozname, počtoch aj hromadnej
úprave), čo vyradí figúrky aj z ponuky volieb panela, okrem Umiestnenia
a Krabice: miesto len s figúrkami tam ostane s nulou setov, inak by
krabica s figúrkami vo filtri chýbala. Do adresy ani do
uloženého pohľadu nejde, takže Prehľad, export, súpis a detail setu počítajú
všetko. Filtre len pre figúrky (Typ, Séria, Podoba, nekompletné, chýbajúce)
a zoskupenie podľa série panel ani `facets()` nemajú; zo stavu účtu ich
Zbierka zahodí (`hasStaleKeys`), starý odkaz s nimi v adrese presmeruje do
Figúrok (`utils/series.ts::figuresRoute`, jedna séria na jej stránku) a
uložený pohľad s nimi je označený a po kliknutí to oznámi
(`hasFigureFilters`). Aby hľadanie figúrky neskončilo tichým „Nič sa
nenašlo“, `FacetsOut.hidden_figures` povie, koľko figúrok zo sérií by filter
našiel, a `FiguresElsewhere.vue` odkáže do Figúrok. Je to nenápadný riadok
pod súčtami, nie `v-alert`, a len keď na tom záleží: hľadanie (`q`) ich
trafilo, filter Umiestnenie či Krabica ich skryl („čo je v krabici 3“
sú aj figúrky), alebo Zbierka nenašla nič (vtedy je riadok v prázdnom
stave). Iný bežný filter s výsledkom nehlási nič. Počty musia patriť tomu
istému hľadaniu a miestu (`filterStore.facetsSearch`, `facetsPlaces`),
inak by po napísaní chvíľu svietil počet zo starého filtra. Pri
spresňovaní hľadania či zmene miesta, ktoré tiež trafilo figúrky, riadok
drží miesto (`pending`, `visibility: hidden`), kým neprídu
nové počty, inak by výsledky pri každej pauze v písaní poskočili. Písmo je
`text-body-medium`: Vuetify 4 má typografiu MD3 a staré triedy
(`text-body-2`, `text-caption`, `text-subtitle-1`…) v jeho CSS nie sú.
Ponuka a hlavička
Zbierky berú `collection_*_count` zo súhrnu, `set_count` a spol. počítajú
všetko. Dlaždica Zbierka na Prehľade nemá vlastné počty, berie tie isté
z `dashboardSummary` (s rozsahom): hlavné číslo `collection_set_count`,
v podnadpise `series_figures` (rôzne figúrky, aj blind-box) a
`sealed_bag_count` (každý nerozbalený sáčok, ako `sealed_bags` vo
Figúrkach). Sáčok nie je figúrka, kým sa nerozbalí, takže bez rozsahu
dlaždica sedí s ponukou aj s Figúrkami. Odkazy z Figúrok na detail nesú
`?from=minifigs`, ponuka potom svieti na Figúrkach
(`utils/navigation.ts::sectionRoute`). Kus pod holým
číslom série je vždy nerozbalený sáčok (`POST /items` ho tak uloží, ako
import), detail série sa pozná podľa `series_size`, nielen podľa kusov
(`utils/series.ts::isSeriesPage`).

**`catalog.kind` hovorí, ako sa položka cení, nie čo to je.** Figúrky
Mighty Machines či Super Mario sú v katalógu `kind=set`, lebo sa cenia ako
sety. Či je kus figúrka zo série, rozhoduje rodič série
(`filters.py::series_of`, `kind_of`); z neho ide `sets_only` Zbierky
a predikáty `kind` a `series` (ostali pre rozsah Prehľadu zo starých
pohľadov a pre detail série). `kind` platí pre cenenie
a pre variant ceny (sáčok, komplet, len figúrka), ktorý majú len skutočné
minifigúrky.

**Zoradenie je jeden register, `services/sorting.py`.** Desať kľúčov
(zisk v € a %, ročný výnos, hodnota, kúpna cena, dátum kúpy, rok, dieliky,
názov, pridané) so smerom `dir`. Zoznam kusov aj zoskupený zoznam idú cez
neho; router nič neradí sám (zoskupený zoznam kedysi zoradenie ignoroval).
Prázdna hodnota (bez ceny, bez dátumu) je vždy na konci, v oboch smeroch.

**Filtre sa skladajú: v skupine ALEBO, medzi skupinami A.** Počet pri voľbe
ráta s ostatnými skupinami, nie s vlastnou, inak by po zaškrtnutí jednej
témy ostatné ukázali nulu. Voľba, po ktorej by nič neostalo, v paneli
zostane a zošedne. Poradie volieb je podľa počtu v celej zbierke
(`universe` v `_options`), nie po filtri, takže zaškrtnutá voľba nevyskočí
navrch; vybraná je červená. Riadok voľby je `components/FilterOption.vue`.
Hodnota „nič“ (bez témy, bez umiestnenia) je `__none__` na oboch stranách.

**Hromadná úprava ide cez filter Zbierky.** `POST /items/bulk-update`
berie tie isté query parametre ako `GET /items` (`FilterDep`); bez
`item_ids` a `catalog_nums` zmení presne to, čo Zbierka s filtrom ukazuje.
Len vlastnené kusy účtu, kategória cez `set_membership` na set,
`dry_run` na počet pred potvrdením (`services/bulk.py`). Figúrky zo sérií
Zbierka nemá, hromadne sa upravujú v detaile série: `BulkBar` tam dostane
`query` `{ series: [num] }` bez `sets_only`, „vybrať všetko“ je celá séria.

**Prehľad počíta rozsah cez ten istý filter.** Všetky `/stats/*` majú
`FilterDep` a filtrujú so stavom „všetko“ (predané v rozsahu ostanú).
Store drží dva súhrny: `summary` za celú zbierku (ponuka, Zbierka)
a `dashboardSummary` pre dlaždice; karty berú `collection.statsQuery()`.

**Umiestnenie má dve úrovne: miestnosť a krabica.** `collection_items.box`
(nepovinné), popis „Povala · krabica 3“ je `place_label` na serveri
a `utils/place.ts::placeLabel` vo frontende, oba rovnako. Formuláre majú
jeden komponent `PlaceFields.vue` (krabice našepkáva podľa miestnosti
z `/suggestions` → `boxes`). Filter Krabica má hodnotu celý popis.
Import, šablóna aj export majú stĺpec `krabica`.

**Tabuľka v Zbierke má pevné šírky a jeden posuvník.** Na širokej
obrazovke virtuálna tabuľka vyplní výsledky (`fill`), riadok musí
odovzdať `itemRef`, inak ukáže len prvých päť riadkov; šírky sú
v `utils/tableColumns.ts` a `table-layout: fixed`, inak sa pri posúvaní
menia. Na telefóne obyčajná tabuľka a posúva sa stránka.

**Zobrazenie je pri účte.** `preferences.display`: tmavý režim, zúžené
bočné menu (rail) a inflácia, cez `composables/useDisplayPrefs.ts`
(`mergeDisplay` nezmaže ostatné polia). Jazyk je `users.locale`.

**Odkaz na pozretie má druh a výber.** `share_links.kind` = `collection`
alebo `wishlist`; `catalog_nums` = len tieto sety (pri sérii celá séria),
None = všetko (`routers/share.py::_chosen`). Odkaz na Chcem ukáže želané
sety, ceny len so zapnutými sumami, poznámky nikdy, zbierku nie.

**Skryť ceny je v jednom formátovači.** `utils/format.ts::pricesHidden`
(ref) prepne `money`/`exactMoney` na „••• €“; každá suma v appke musí ísť
cez ne, inak by pri ukazovaní portfólia ostala vidieť. Grafy majú v
možnostiach závislosť na `pricesHidden`, aby sa prekreslili. Stav je
v `preferences.display.hidePrices`.

**Kategórie visia na sete, nie na kuse.** Set patrí do kategórie podľa
pravidiel (názov, téma, podtéma; celé slovo, obsahuje, presne), alebo ručne.
Prednosť: ručná voľba na sete, potom ručná voľba na jeho sérii, potom
pravidlá. Ručný záznam sa ukladá, len keď mení výsledok
(`services/categories.py::set_membership`), takže vylúčenie proti pravidlu
je riadok s `mode=exclude`. Nový účet začína bez kategórií; „Formula 1“
z migrácie ostala len starším účtom. Vo formulári (Pridať set aj úprava
kusu) je výber jeden: `components/CategoryPicker.vue` so stavom
`composables/useCategoryPicker.ts` u rodiča. Zapisuje sa až pri uložení
formulára a len kategórie, kde sa výber líši od stavu servera; detail
setu (`CategoryMembership.vue`) zapisuje hneď po kliknutí.

**Cena pre druhý stav je lepšia než žiadna.** Zdroj vracia cenu použitého
kusu len pri stiahnutých setoch. Postavený kus setu, ktorý je ešte v predaji,
by tak zostal bez hodnoty. `SnapshotIndex.value_at_any` spadne na druhý stav
a označí to ako `price_source="market_approx"`; rozhranie pred takú sumu dáva
znak ≈. Graf portfólia aj pohyby cien musia vidieť to isté, inak si tri
obrazovky protirečia.

**Detail setu si kusy načítava sám so `status=all`.** Zoznam v Zbierke je
filtrovaný a po predaji by predaný kus z detailu zmizol aj s históriou.

**Moje kusy v detaile setu sú jedna mriežka.** Stĺpce (štítky, Kúpené,
Hodnota, Zisk, akcie) určuje len `.pieces-grid` v `SetDetailView.vue`;
riadok kusu aj oba súčty sú `subgrid` s tými istými piatimi bunkami
`piece-cell--…` v tom istom poradí (stráži `SetDetailView.spec.ts`).
Vlastné šírky riadku ani flex s medzerami podľa obsahu nie: pri inom
počte štítkov by sumy odskočili a súčet by nestál pod nimi. Rozloženie
mení šírka karty (`@container`), nie okna: nad 840 px jeden riadok, do
840 štítky nad sumami, do 640 tri rovnaké stĺpce súm a akcie pod nimi.

**Každé volanie cudzej služby má schopnosť a prejde bránou.** Register je
`capabilities.py` (`Cap`, `CAPABILITIES`, `PROVIDERS`). Zdroj pred požiadavkou
zavolá `fetch_policy.ensure_allowed(policy, cap)`: vypnutá schopnosť alebo
volanie na pozadí pri rezerve (Brickset predvolene 20) vyhodí `CallBlocked`
a požiadavka neodíde. Volajúci ho spracuje po svojom (pridanie setu bez
Brickset, dopĺňanie sa zastaví a set neoznačí, kód skúsi ďalší zdroj).
Pravidlá sú pri účte (`users.fetch_settings`) a cestujú v `UserKeys.policy`,
zdroje sa vytvárajú cez `…Provider.for_user(settings, keys)`. Schopnosť je
povinná len pri dvojznačných metódach (Brickset `get_item`, BrickEconomy
`get_market`); minutý limit BrickEconomy hlási ďalej `QuotaExhausted`.
Nové volanie von = nový riadok v `CAPABILITIES` a texty v `locales`
(`capabilities.<služba>.<meno>`, vnorene, bodku berie vue-i18n ako cestu).

**Každé volanie sa zapisuje so schopnosťou.** `api_log.record(..., cap=)`,
tabuľka `api_calls`, 30 dní. Čie je volanie, nastaví `api_log.set_user`
(závislosť prihláseného používateľa, úlohy na pozadí). Prehľad limitov je
`GET /usage` a ikona v hornej lište; Brickset dáva vlastnú štatistiku.

**Nastavenia → Dáta sú karty služieb.** `GET/PUT /auth/me/sources`,
`components/SourcesPanel.vue` a `SourceCard.vue`. `ApiKeysOut.capabilities`
je zoznam, čo účet smie; rozhranie skrýva cez `auth.can(cap)` (tlačidlo cien,
Témy, dlaždice hodnoty, odhad rastu), nie cez vlastné podmienky na kľúče.

**Overiť cenu je jedno volanie servera.** `POST /prices/lookup/{num}`
(`routers/prices.py::lookup_price`): katalóg, potom Rebrickable, a keď set
nepozná nikto, odpoveď BrickEconomy o cene poslúži aj ako metadáta (názov,
séria, rok, dieliky; `MarketData.name` a spol.), takže jedno volanie dá
set aj cenu. Holé číslo skúša len variant `-1`. Cena mladšia než 24 h sa
neťahá (`price="cached"`). Neúspech (zdroj set nepozná alebo nemá
cenu) zapíše `pricing.store_miss` ako v obnove cien: 24 h v procese
(`services/price_misses.py`) a `miss:` pri kľúči, takže set vynechá aj
dávka. Výpadok siete, 5xx či 429 (`provider.last_answered` je False) sa
nezapíše nikde. Holá figúrka (`fig-…`) sa neceni vôbec: inak by každý
opakovaný sken stál volanie. `outcome` a `price` sú kódy, texty robí
frontend; `no_sources` = neznámy set a nie je kto ho dohľadať. Overené
sety sú v `price_checks` pri účte; `/prices/checks` je v routeri pred
`/prices/{num}`, inak by ho zhltol. Klik na riadok tabuľky nevolá von.

**Obnova cien nemá plánovač a nespúšťa ju prihlásenie.** Spúšťa ju výhradne
používateľ tlačidlom v hornej lište (`POST /prices/refresh-all`), ďalej to
beží cez `BackgroundTasks`. Stav „beží“ zaberá už požiadavka
(`refresh.claim`), úloha ho len uvoľní (`claimed=True`): úloha štartuje až
po odpovedi a bez toho by 202 aj ďalší `refresh-status` hlásili „nebeží“,
takže prvé kliknutie akoby nič nespravilo. Frontend berie stav z odpovede.
Poistky sú v `services/refresh.py`: vek posledného volania, strop na dávku,
zvyšok dennej kvóty, jedno volanie na položku a zámok proti súbehu. Do stropu idú najprv neznáme ceny.

**Registráciu otvára správca v appke, nie `.env`.** Stav je v tabuľke
`app_settings` (`services/app_settings.py`); `ALLOW_REGISTRATION` platí,
len kým ho správca nezmení. Prvý účet sa zaregistruje vždy, inak by nová
inštalácia nemala správcu. Prihlasovacia stránka si stav pýta sama cez
`/providers/status`, lebo na verejnej stránke sa relácia neobnovuje.

**Čiarový kód: doma, potom Brickset, potom UPCitemdb.** Brickset (kľúč
používateľa, 100 volaní denne) hľadá podľa kódu cez `getSets` s `query`
a výsledok sa overí proti `barcode` v odpovedi, lebo dotaz môže trafiť aj
názov. Kód z Brickset ide do `brickset_facts` s prístupom `ean:{kód}`,
kód z UPCitemdb do `catalog_items.ean` s `ean_source`. Nový set
naskenovaný cez Brickset stojí dve jeho volania (hľadanie a doplnenie
metadát). `normalize_ean` je v `lego_api/ean.py`, samostatne, inak vznikne
kruhový import zdrojov a služieb.

**Popis, štítky a hodnotenie sú z Brickset, raz na set.** `getSets`
s `extendedData: 1` (ráta sa ako jedno volanie) dá oficiálny popis, štítky,
hodnotenie a obľúbenosť. Nové sety ich dostanú pri vyhľadaní; staršie dopĺňa
`services/brickset_extras.py` na pozadí pri otvorení Zbierky, najviac 40 za
beh, a detail setu pri otvorení (jedno volanie). Prístup kľúča v
`source_access` (aj pri nenájdenom sete, `found=False`) stráži, aby sa ten
istý kľúč na set nepýtal znova. Štítky sú aj filter: štítok v detaile
setu vedie do Zbierky s ním, na detaile figúrky zo série (aj série samej)
je obyčajný čip, lebo Zbierka figúrku neukazuje.

**Ďalšie fotky setu sú z Brickset, raz na set.** `getAdditionalImages`
sa do limitu nepočíta, ale chce `setID` Brickset, nie číslo setu. `setID`
a `additionalImageCount` prichádzajú v každom getSets (`apply_brickset`
ich uloží do `brickset_id`, `bs_image_count`). `GET /catalog/{num}/images`
galériu stiahne raz do `bs_images` (prázdny zoznam = nemá, nepýtať sa);
set bez `brickset_id` sa najprv raz opýta cez getSets. Prepínač
`brickset.images` vypne galériu aj volanie. Obrázky sa načítavajú priamo
z Brickset s „Image(s) courtesy of Brickset.com“; detail pýta galériu až
po doplnení z Brickset, inak by išli dve getSets naraz.

**Témy a vlny sú z Brickset.** `getThemes` a `getYears` sa do limitu
nerátajú, vlna (téma + rok) je jedno `getSets` a ukladá sa do `theme_waves`
a `theme_wave_sets`; čerstvé roky sa po 30 dňoch stiahnu znova. Kolekcie
a iné nie-sety (`category` mimo Normal/Extended) do úplnosti nepatria.
Témy pomenúva Brickset, katalóg má tému z Rebrickable a nezhodujú sa
(staršie Botanicals má Brickset pod Icons, figúrky série Shrek Rebrickable
pod Shrek). Set sa preto ráta v jedinej téme podľa `themes.py::assign`:
stiahnutá vlna, ktorú účet vidí, potom `bs_theme`/`bs_year` (brickset_facts,
len s prístupom kľúča), až keď Brickset set nepozná, téma a rok z katalógu.
Nie-set je, čo má v `brickset_facts.category` inú kategóriu než
Normal/Extended; staršie údaje ju nemajú a vtedy set vyradí len vlna jeho
témy a roka stiahnutá neskôr, než Brickset o sete odpovedal (`fetched_at`).
Vlna staršia než údaj setu je stará: set sa ráta, rok je odhad (≈)
a otvorenie roka ju stiahne znova hneď (`_outdated`, jedno getSets, potom
je vlna novšia a znova nie). Set bez údajov Brickset sa podľa roka
z Rebrickable nezahadzuje, v stiahnutej vlne je len odhad.
Rátajú sa len sety (`counts_as_set`: nie figúrky zo sérií podľa
`filters.series_num`, sáčok pod číslom série ani holá figúrka), aj vo vlne
a v počte Sérií v ponuke (`theme_names`). Ten ráta len témy zo zoznamu
Brickset ako `overview` (`known_themes`, zoznam v pamäti procesu); kým
zoznam nie je načítaný, len témy od Brickset, nie mená z Rebrickable
(podtéma Modular Buildings v Brickset nie je). „V zbierke“ je najviac počet
setov témy či roka; či je téma naozaj celá, povie `ThemeOut.complete`
(úplná zhoda a vo vlnách nič nechýba) a len vtedy je `SeriesBar` zelený,
aj filter Nekompletné ide podľa neho. Prop `complete` má predvolené
`undefined`, chýbajúci boolean by Vue zmenilo na false. Kým vlna nie je
stiahnutá, počet pri roku je odhad, potom presný; odhad ostane, keď v nej
chýba môj set (stará vlna, ktorú brána nepustila stiahnuť znova):
`ThemeWaveOut.exact` je False, počty aj sety vlny ho rátajú ako `years()`
a otvorený rok čip neprepne na presný. Existujúcim setom
Brickset nič neprepisuje, len dopĺňa chýbajúce.

**UPCitemdb je posledná možnosť.** Rebrickable kódy
nemá a BrickEconomy podľa kódu hľadať nevie (kód len posiela v odpovedi
o cene, `apply_catalog_extras` ho uloží). `services/barcode.py` skúsi
katalóg, potom UPCitemdb (zadarmo, bez kľúča, ~100 dotazov denne), z názvu
produktu vyčíta číslo setu a overí ho cez Rebrickable. Nájdený kód sa uloží,
ďalší sken toho istého setu už von nejde. Kontrolná číslica sa overuje pred
dotazom. Čítačka v prehliadači (`BarcodeScanner.vue`) berie ZXing wasm zo
súborov appky, nie z CDN; kamera ide len na https alebo localhost.
UPCitemdb LEGO kódy pozná len čiastočne. Neznámy kód si pridávanie
pamätá a po uložení ho cez `PUT /catalog/{num}/ean` priradí setu zadanému
číslom, takže ďalší sken ho nájde doma. Čítačka popri celom zábere skúša
zväčšený stred a „vyrovnaný tieň“ (obraz delený svojou rozmazanou kópiou);
bez toho ZXing skutočnú fotku krabice s tieňom neprečítal vôbec.

**Ručná čítačka ide cez `stores/scanner.ts`, nie cez pole formulára.**
Čítačka v režime klávesnice (HID) „píše“ rýchlo a stlačí Enter; detektor
(`scanner/codes.ts`) to spozná podľa medzier pod 40 ms, sken zastaví
a odovzdá ho poslednému odberateľovi `useScanCodes`. Web Serial appka
nemá, Honeywell ide ako klávesnica. `AppLayout` je odberateľ-záloha
(`fallback: true`, zaradí sa na spodok, lebo rodič sa pripája až po
deťoch) a sken z inej obrazovky pošle na `/pridat?code=`. Pridať set
rozhoduje cez `scanner/scanFlow.ts::decideScan`: rovnaký kód = počet + 1,
iný kód = uložiť rozpracovaný set (oznámenie so Späť) a načítať nový.
Skeny aj tlačidlo Uložiť idú cez jednu frontu (`enqueue`), inak by rýchly
druhý sken uložil set dvakrát. Znak sa berie z fyzickej klávesy
(`event.code`, `scanChar`), nie z `event.key`: čítačka posiela klávesy
americkej klávesnice a slovenské rozloženie by z 5702017817767 urobilo
„ťýéľé+ýá+ýýžý“.

**Bez kľúča Rebrickable sa set uloží ručne len číslom.** `POST /catalog`
má názov nepovinný („Set 10294“) a holé číslo zmení na `10294-1`, rovnako
ako Rebrickable, inak by po pripojení kľúča vznikol set druhý raz.
Pridať set to pozná cez `auth.can('rebrickable.set')`.

**Neúspešný kód sa 30 dní nehľadá znova.** `barcode_misses` pri účte
(Brickset hľadá pod kľúčom účtu), len `not_found` a `no_set_number`.
Katalóg má prednosť pred zapamätaným neúspechom, `?retry=true` ho obíde,
nájdený aj ručne priradený kód ho zmaže.

**Oznámenia sú jeden store.** `stores/notify.ts` a `v-snackbar-queue`
v `AppLayout`. Každé pridanie, úprava a zmazanie volá `notify.success`
alebo `notify.error`; vlastný `v-snackbar` v komponente nie. Tlačidlo
v oznámení (Späť) drží store podľa `data-notice`, lebo vlastnosti správy
idú rovno do `v-snackbar` a funkcia by skončila ako atribút v HTML.
Chyba poľa formulára ostáva pri poli.

**Načítavanie nie je prázdny stav.** Kým server neodpovedal, stránka ukáže
kostru (`components/PageSkeleton.vue`: dlaždice a grafy Prehľadu, karty,
riadky, tabuľka, detail setu), nie „Zatiaľ žiadne sety“ ani nuly, inak to
vyzerá, že zbierka zmizla. Prázdny stav až po odpovedi, chyba prvého
načítania je `LoadFailed.vue` („Nepodarilo sa načítať“ so Skúsiť znova).
Stav drží `composables/usePageLoad.ts`: načítanie vráti `false` (alebo
vyhodí), keď zlyhalo, `{ data }` bez kontroly `error` by chybu zmenilo na
prázdny zoznam. Opakované načítanie (filter, rozsah, Obnoviť stránku) nechá
staré dáta a rozsvieti len pruh pod hornou lištou (`pageBusy`); chyba vtedy
ide do oznámenia. Iný obsah na tej istej trase (iný set, séria, rok)
začína `reset()`, teda znova kostrou. Počty v ponuke bez súhrnu nie sú 0,
ale nič (`undefined`). Tlačidlo Obnoviť stránku v hornej lište (na telefóne
v menu účtu) volá `reloadPage`: každý `usePageLoad` sa prihlási sám, karta
s vlastným načítaním cez `onPageReload(load)`, a súhrn za ponukou sa
dotiahne, keď ho nenačíta stránka (Prehľad má `summary: true`). Prihlasujú
sa len GET na vlastný server; doplnenie z Brickset, obnova cien ani iné
volanie von do neho nepatria. Kosti `v-skeleton-loader` farbí
`styles/settings.scss` (téma má `border-opacity` 1, kosti by boli čierne).

**Čísla v ponuke obnovuje klient, nie obrazovka.** Úspešná zmena kusov,
Chcem alebo potvrdený či vrátený import (`api/client.ts::changesMiddleware`,
`COLLECTION_CHANGES`) zavolá odberateľov `onCollectionChanged`; store
zbierky po 250 ms načíta `/stats/summary` (`loadSummary`). Obrazovka, ktorá
medzitým zavolá `refreshAll`/`loadDashboard`, plánované načítanie zruší,
takže súhrn nejde dvakrát. Kedysi to musela robiť každá obrazovka sama a Mám
ju či srdiečko na chýbajúcej figúrke ponuku neobnovili. Nová cesta, ktorá
mení počty, = riadok v `COLLECTION_CHANGES`, nie volanie v komponente.

**Pamäť formulára je pri účte.** `preferences.form` (`remember`, `last`),
`composables/useFormMemory.ts`. Zapisujú sa všetky polia po každom
uložení, predvypĺňajú len zapnuté. Nový formulár na pridávanie kusov
volá `memory.initial()` pri otvorení a `memory.remember()` po uložení.

**Doplnená kúpna cena je označená.** Prepínač `auto_purchase_price` na
karte BrickEconomy; `services/purchase_fill.py` beží v `finally` obnovy
cien, pri zapnutí prepínača (`PUT /auth/me/sources`) a v `refresh-all`
pri minutej kvóte, vždy zadarmo. BrickEconomy RRP z odpovede má
prednosť pred `catalog.rrp_eur`. `purchase_price_auto` zruší každý PATCH
s `purchase_price_eur`, preto dialóg kusu posiela cenu len pri zmene
(`utils/priceEdit.ts`).

**Kľúče k cudzím službám nie sú v konfigurácii.** Patria používateľovi, sú
uložené zašifrované pri jeho účte (`services/keys.py`) a do poskytovateľa
sa dostanú cez závislosť `CurrentKeys`. `Settings` ich nepozná, takže
provider bez kľúča je jednoducho vypnutý. Kľúč sa nikdy nevracia z API, von
ide len koncovka z `mask()`. Denná kvóta sa počíta podľa odtlačku kľúča,
nie podľa účtu.

**`Literal` na číselnom query parametri nefunguje.** Hodnota príde ako
reťazec a `Literal[30, 90, 365]` na `"90"` spadne na 422. Pri číslach
kontroluj rozsah v tele funkcie (`routers/stats.py::get_movers`).
Pri reťazcoch (`Literal["day", "week"]`) je to v poriadku.

**Pri vypnutých sumách sa ceny do verejnej odpovede vôbec nevkladajú.**
Nie sú teda ani v zdrojovom kóde stránky. Neriešiť to skrývaním vo frontende.

**index.html sa nesmie kešovať.** Servuje ju `main.py::spa` s
`cache-control: no-cache`, súbory s otlačkom v názve naopak na rok.
Bez toho si prehliadač podrží starú stránku, ktorá ťahá staré skripty,
a používateľ vidí appku spred opravy. Prejaví sa to ako „opravil si to,
ale nefunguje to“.

**Súbory na stiahnutie nejdú obyčajným odkazom.** Prihlásenie je token
v pamäti, nie cookie, takže `<a href="/api/v1/...">` odíde bez neho a stiahne
sa 401. Sťahuje sa cez klienta a blob (`components/ExportCsvButton.vue`).
CSV začína BOM, inak Excel rozbije diakritiku.

**Zapamätanie prihlásenia volí používateľ políčkom.** „Zapamätať si
prihlásenie na tomto počítači“ je pri prihlásení aj registrácii, predvolene
nezaškrtnuté, a posiela `remember`. So zapamätaním je `lego_refresh` trvalé
cookie na `refresh_token_days` (30), bez neho session cookie bez Max-Age
a token na serveri platí `refresh_session_hours` (12 h): prehliadač
s obnovou kariet vráti aj session cookie. Režim je v `refresh_tokens.remember`,
obnova tokenu ho zdedí a platnosť posunie (kĺzavé). Tokeny spred stĺpca sú
bez zapamätania, inak by kĺzavých 30 dní ostalo trvalých naveky; migrácia
`9332cb64e9a6` im skrátila platnosť na 12 h. Výmena pri obnove je atómová
(`UPDATE … WHERE revoked_at IS NULL`, rowcount): z kariet s tým istým cookie
vymení token len jedna. Vymenený token do `refresh_grace_seconds` (60 s)
dá prístup aj vlastný nový token v tom istom režime (súbežné karty po
reštarte prehliadača, stratená odpoveď s cookie pri F5): bez neho by
prehliadač držal vymenený token a po lehote by to vyzeralo ako krádež.
Po lehote je to ukradnuté cookie:
zmažú sa všetky tokeny účtu a do logu ide varovanie. Vymenený token preto
ostáva do vypršania, bez `user_agent`. Vypršané tokeny všetkých účtov maže
`auth/tokens.py::prune` pri každom vydaní aj pri štarte, zásady sľubujú
najviac 30 dní. Odhlásenie zmaže len aktuálny token (vymenené ostanú, inak
by odhlásenie na telefóne zmazalo stopu ukradnutého cookie z PC), zmazanie
účtu všetky (`_OWNED`). Zmena hesla (`_end_logins`) zmaže všetky
tokeny účtu a nastaví `users.password_changed_at`: `current_user` odmietne
prístupový token so starším `iat` (na celé sekundy), takže iné zariadenia
stratia prístup hneď. Tento prehliadač dostane nový token v tom istom
režime (zapamätanie ostane) a nový prístupový token si vezme hneď
(`stores/auth.ts::updateProfile`); inak ho obnoví 401 v `api/client.ts`,
ktorý si kópiu požiadavky s telom robí pred odoslaním, lebo odoslané telo
sa zopakovať nedá. `restore()` ide cez tú istú `refreshSession`.
Zmena trvania = text zásad (Ako dlho, tabuľka cookies) a `privacy_version`.
V desktope cookie drží most a trvalé ukladá do `session.bin` (pozri hore).

**Filter Zbierky si pamätá účet, nie prehliadač.** `users.preferences`
(JSON, kľúč `collection`) cez `/auth/me/preferences`, v prehliadači
`stores/preferences.ts` s oneskoreným ukladaním. Príchod bez filtra v adrese
(z ponuky) vráti posledný stav; odkaz s filtrom má prednosť a stane sa novým
posledným. Predvolený stav sa neukladá (prázdny objekt stav zmaže).
Zoradenie je v adrese ako `sort`, len keď nie je predvolené.

**Zbierka na širokej obrazovke nesmie byť vyššia než okno.** Trasa má
`meta.fitScreen`, rozloženie potom vynechá dolnú rezervu a posúva sa len
panel filtrov a výsledky, nie stránka. Na telefóne sa posúva normálne.
Do výšky rastie len `.collection-results`, ostatné riadky `.collection-main`
majú `flex: 0 0 auto`: `v-alert` a `v-banner` majú vo Vuetify `flex: 1 1`
a v stĺpci na výšku okna by si s výsledkami rozdelili miesto napoly
(upozornenie o figúrkach tak raz zabralo pol obrazovky). Overiť cenu to má
rovnako (`.check-page--fit > *`).

**V dnešných peniazoch je prepočet na serveri, nie vo frontende.**
`services/inflation.py` ťahá mesačný HICP Slovenska z Eurostatu
(`prc_hicp_minr`, `coicop18=TOTAL`, `unit=I15`; starý `prc_hicp_midx` končí
2025-12) do tabuľky `inflation_index`, raz za týždeň a len keď si ho niekto
vypýta. Po chybe hodinu pokoj, starý rad ostáva. Kúpna cena sa násobí
`index(posledný) / index(mesiac kúpy)`, predajná podľa mesiaca predaja,
trhová hodnota je dnešná a nemení sa. `deflate` nastaví `buy_factor`
a `sell_factor` na `ValuedItem`, takže súhrn, zisk, CAGR, rozpad aj graf
idú samé. Trasy berú `real=true`; súhrn vracia `real_month`, prázdny = index
chýba a sumy sú nominálne. Priemerná zľava voči RRP ostáva nominálna.
Riadok súčtov nad kartami Zbierky (`FacetsOut.totals`) ukazuje reálny zisk
len pri zapnutom prepínači inflácie. Testy majú `inflation_enabled`
vypnuté, aby nešli na sieť; `test_inflation.py` si ho zapína.

**Import nepýta ceny ani Brickset.** `services/importer.py` dohľadáva
neznáme čísla cez `CatalogService` s vypnutým Brickset: bežné `resolve` volá
aj `getSets` a stovky setov by minuli jeho denný limit. Nič sa neuloží, kým
používateľ nepotvrdí náhľad. Kusy a Chcem z importu majú `import_batch_id`
a vrátenie maže podľa neho, aj s fotkami, a obnoví, čo import vyradil
z Chcem. Duplicita je rovnaký set s rovnakým dátumom a cenou, takže opätovné
nahratie súboru nič nezdvojí. Stĺpce importu, šablóny a exportu sú tie isté;
pri pridaní stĺpca uprav všetky tri.

**Dátum sa zadáva cez `DateField.vue`, nie `type="date"`.** Obal nad
`v-date-input` drží text `RRRR-MM-DD` a prevádza cez miestny čas;
`toISOString` by z polnoci posunul dátum o deň. Jazyk Vuetify ide za
jazykom appky (`App.vue`), inak kalendár čaká mm/dd/rrrr.

**Textové polia s históriou idú zo servera.** Kde uložené, Kde kúpené
a kanál predaja sú `v-combobox` s hodnotami z `GET /suggestions`
(`services/collection.py::known_suggestions`), nie z histórie prehliadača,
ktorá je len na jednom zariadení. Combobox pri vymazaní vráti `null`,
preto `(x.value ?? '').trim()`. Dnešný dátum je `utils/format.ts::isoDate`,
nie `toISOString`, ten je v UTC.

## Slovenčina

Množné číslo má tri tvary: 1 set, 2 až 4 sety, 5 a viac setov. Vlastné
pravidlo je v `plugins/i18n.ts`, kľúče končia na `Plural` a volajú sa cez
`t('collection.setsPlural', count, { named: { count } })`.

Čísla formátuje `utils/format.ts`. Tisíce oddeľuje nezlomiteľná medzera, aby
sa suma nezlomila do dvoch riadkov. Desatinná čiarka, znak eura za číslom.

## Triedy písma sú z Vuetify 4

Vuetify 4 nemá `text-caption`, `text-body-2`, `text-h6` a ostatné triedy
z Vuetify 3; trieda bez štýlu nič nehlási a text ostane veľký ako rodič.
Používaj `text-body-small` (namiesto caption), `text-body-medium` (body-2),
`text-body-large` (body-1, subtitle-1), `text-title-small` (subtitle-2),
`text-title-large` (h6, s `font-weight-medium`), `text-headline-small` (h5),
`text-headline-large` (h4) a `text-label-medium text-uppercase` (overline).
Stráži to `utils/typography.spec.ts`.

## Vlastné komponenty treba importovať

Vuetify komponenty sa doťahujú samé, tie moje nie. Chýbajúci import sa
prejaví ako prázdne miesto bez chyby v type-checku. ESLint to nezachytí,
takže pri pridaní komponentu do šablóny skontroluj import.

## Testy

Backend má 757 testov, frontend 273. Jadro logiky je pokryté v `test_portfolio.py`,
`test_pricing.py`, `test_refresh.py`, `test_insights.py`, `test_inflation.py` a `test_import.py`, poskytovatelia v `test_providers.py`
bežia proti uloženým JSON odpovediam cez `respx`, teda bez siete. Fixtúry
majú tvar reálnych odpovedí, vrátane setu, ktorý je ešte v predaji a nemá
teda ani použitú cenu, ani históriu. Ceny BrickEconomy v nich sú vymyslené:
ich údaje sa podľa podmienok nesmú šíriť.

`conftest.py` nastavuje len tajomstvo a databázu v pamäti. Kľúče v ňom byť
nemusia, konfigurácia ich nepozná.

Frontend testuje aj komponenty so skutočným Vuetify
(`components/PieceDialog.spec.ts`): komponenty Vuetify sa registrujú
v teste, jsdom potrebuje náhradu `ResizeObserver` a `visualViewport`
a `vitest.config.ts` spracúva Vuetify cez Vite (`server.deps.inline`).

Stránka so storom v teste (`views/CollectionView.spec.ts`) dostane piniu
výslovne (`plugins: [pinia]`, `useFilterStore(pinia)`) a `enableAutoUnmount`.
Akcia pinie prepne aktívnu piniu na svoju, takže oneskorené načítanie
stránky z predošlého testu by `useFilterStore()` bez parametra podstrčilo
cudzie úložisko a test by občas padal.
