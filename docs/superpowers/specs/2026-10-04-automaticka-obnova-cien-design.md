# Automatická denná obnova cien (desktop)

Stav: schválené 2026-10-04 (čas cez komponent Vuetify). Po kontrole: úloha na
používateľa Windows (`Moje kocky\Obnova cien - <meno>`), chyba Plánovača
v rozhraní, beh s viditeľnosťou účtu, dobehnutie len zvyšku počtu, zastavenie
pri výpadku siete s pokusom o 30 minút, čas sa uloží až pri OK.

## Cieľ

Ceny BrickEconomy sa obnovia každý deň v nastavený čas aj vtedy, keď Moje
kocky nie sú otvorené. Stačí, aby bol počítač zapnutý a používateľ
prihlásený do Windows. Nič sa nevolá bez kľúča BrickEconomy a bez výslovného
zapnutia.

Čo povedal používateľ:
- prepínač v Nastaveniach;
- čas si nastaví sám, predvolene 7:00;
- počet cien na jeden beh, predvolene 80;
- riešenie cez Plánovač úloh Windows, ako v prieskume.

Ostatné sú moje predpoklady.

## Rozhranie

Nastavenia → Dáta → karta BrickEconomy, len v desktope (`isDesktop`):
- **Prepínač** „Obnovovať ceny automaticky každý deň“.
  - Bez schopnosti `brickeconomy.prices` (`auth.can`) je zakázaný, s vysvetlením
    „Treba kľúč BrickEconomy“. Ostatné schopnosti sa riadia rovnako.
- **Čas:** `components/TimeField.vue`, predvolene 07:00. Je to obal ako `DateField.vue`: pole na čítanie, ktoré otvorí `v-time-picker` z Vuetify (`format="24hr"`) v `v-menu` a drží text `HH:MM`. Nie `type="time"`.
- **Počet cien na jeden beh:** predvolene 80, najviac denný limit (100).
  - Beh berie najviac zvyšok dňa (`calls_left`), takže ručné kliknutie v ten
    deň ho môže skrátiť.
- **Riadok stavu pod prepínačom:**
  - „Naposledy automaticky: dnes 7:02, obnovené 23 cien“;
  - pri chybe „Naposledy automaticky: 7:00, nepodarilo sa (BrickEconomy
    neodpovedá)“.
  - Ten istý údaj ukáže aj tooltip tlačidla obnovy v hornej lište.

Pre web (Docker) sa v tomto kroku nič nemení. Dialóg obnovy ani tlačidlo
v lište sa nemenia.

## Uloženie nastavení

`users.preferences.autoRefresh = { enabled, time: "07:00", limit: 80 }` pri
účte, cez `/auth/me/preferences`. Do `PREFERENCE_KEYS` pribudne
`autoRefresh`.

Výsledok posledného behu je v `app_settings` → `auto_refresh_last`:
`{ user_id, at, updated, outcome }`. Rozhranie ho číta cez
`GET /prices/refresh-status` (nové pole `auto_last`), len pre vlastný účet.

Je to údaj o behu, nie osobný údaj navyše. V zásadách netreba novú vetu.
Plánovač úloh je mimo databázy, preto do tabuľky úložísk na `/sukromie`
pribudne riadok: „Úloha v Plánovači úloh Windows (Moje kocky\Obnova cien),
kým je automatická obnova zapnutá“. Zvýši sa `privacy_version`.

## Plánovač úloh Windows

- **Zapnutie, zmena času aj vypnutie** idú cez metódu mosta (`Bridge`,
  nie HTTP API). Tá zavolá `schtasks` v kontexte prihláseného používateľa,
  bez práv správcu.
  - Zapnutie: `schtasks /Create /TN "Moje kocky\Obnova cien" /XML <dočasný
    súbor> /F`.
  - Vypnutie: `schtasks /Delete /TN "Moje kocky\Obnova cien" /F`.
- **XML úlohy:**
  - `CalendarTrigger`, denne v čase z nastavení;
  - `LogonType=InteractiveToken`, teda len pri prihlásenom používateľovi,
    bez uloženého hesla;
  - `StartWhenAvailable=true`, aby zmeškaný beh dobehol po zapnutí PC;
  - `DisallowStartIfOnBatteries=false`;
  - `ExecutionTimeLimit=PT30M`;
  - akcia: `"{app}\MojeKocky.exe" --refresh-prices`.
- **Viac účtov:** úloha je jedna, jej čas je najskorší čas zo zapnutých
  účtov. Beh obnoví každý zapnutý účet, ktorému už nastal jeho čas a dnes
  ešte nebežal. Ostatné dobehnú v otvorenej aplikácii (nižšie).
- **Odinštalovanie** úlohu zmaže (`[UninstallRun]` v `moje-kocky.iss`, chyba
  sa ignoruje).
- **Prenos medzi počítačmi:** úloha neputuje s databázou. Pri štarte
  aplikácia porovná nastavenie účtu s tým, či úloha existuje, a chýbajúcu
  vytvorí znova. Rovnako po preinštalovaní.

## Beh bez okna (`--refresh-prices`)

`lego_desktop.main` pri argumente `--refresh-prices` neotvorí okno:
1. **Zámok:** vezme ten istý zámok inštancie (`DataDir.lock`, jeden proces
   nad SQLite). Keď aplikácia beží, skončí hneď a obnovu urobí otvorená
   aplikácia sama.
2. **Prostredie:** nastaví `os.environ` z `DataDir.environment()` a log do
   `logs/moje-kocky.log`. Pustí migrácie ako bežný štart, so zálohou pri
   novej verzii.
3. **Obnova:** pre každý zapnutý účet, ktorému nastal čas a dnes ešte nebežal:
   - kľúče cez `keys_of`, `api_log.set_user`;
   - `refresh_prices(..., batch=limit)` s tými istými poistkami ako
     tlačidlo: vek týždeň, najprv neznáme ceny, zvyšok kvóty a rezerva
     `brickeconomy.prices`;
   - potom `fill_purchase_prices`, ako po ručnej obnove;
   - výsledok zapíše do `auto_refresh_last`.
4. **Uvoľnenie a koniec:** zámok uvoľní a proces skončí. Okno ani oznámenie
   sa neukážu.

**Otvorenie aplikácie počas behu.** Beh pred každým volaním skontroluje súbor
`auto-refresh.stop` v priečinku údajov. Aplikácia, ktorá pri štarte nájde
obsadený zámok a súbor `auto-refresh.running`, vytvorí `auto-refresh.stop` a
čaká najviac 30 s na zámok. Beh dokončí rozbehnuté volanie, zapíše výsledok
a skončí. Zvyšok obnoví otvorená aplikácia. Bez súboru `.running` sa ukáže
doterajšie „Moje kocky už bežia“.

## Obnova v otvorenej aplikácii

V lifespan aplikácie, len v desktope, beží úloha, ktorá raz za minútu
skontroluje zapnuté účty. Keď účtu nastal čas a dnes ešte neprebehol celý
automatický beh, spustí ho cez `refresh.claim`, teda nie súbežne s ručnou
obnovou. Pokryje to:
- aplikáciu otvorenú o 7:00;
- beh prerušený otvorením aplikácie;
- ďalšie účty s neskorším časom.

## Kvóta a cena

Jeden beh je najviac `limit` volaní (predvolene 80 zo 100 denne) a nikdy nie
viac, než dnes ostáva. Rezerva `brickeconomy.prices` platí ako pri dávke.
Ceny mladšie než týždeň sa nevolajú, takže pri menšej zbierke beh obnoví
len zastarané ceny a väčšinu dní nemíňa skoro nič.

## Pravidlo v CLAUDE.md

Mení sa veta „Obnova cien nemá plánovač a nespúšťa ju prihlásenie“ na:
spúšťa ju používateľ tlačidlom, alebo plánovač, ktorý si sám zapol v desktope;
prihlásenie ju nespúšťa nikdy.

## Testy

- **Backend:**
  - výber účtov na beh (čas, dnes už bežal, bez kľúča nie, vypnuté nie);
  - `--refresh-prices` skončí, keď je zámok obsadený;
  - zastavenie cez `auto-refresh.stop`;
  - zápis `auto_refresh_last`;
  - `refresh-status.auto_last` len vlastného účtu;
  - kvóta: `limit` aj zvyšok dňa.
- **Desktop:**
  - XML úlohy (čas, `StartWhenAvailable`, `InteractiveToken`, cesta k exe);
  - príkazy `schtasks` cez náhradu `subprocess`;
  - `[UninstallRun]` v `.iss` (`test_installer.py`).
- **Frontend:**
  - prepínač zakázaný bez `brickeconomy.prices`;
  - čas a počet sa ukladajú do `preferences.autoRefresh`;
  - riadok „Naposledy automaticky“.

## Mimo rozsahu

- Web (Docker) plánovač. Dá sa doplniť neskôr tým istým výberom účtov
  v lifespan servera.
- Prebudenie počítača zo spánku (`WakeToRun`) a oznámenie Windows po behu.
