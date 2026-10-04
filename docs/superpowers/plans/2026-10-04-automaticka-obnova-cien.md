# Automatická denná obnova cien: plán

Spec: `docs/superpowers/specs/2026-10-04-automaticka-obnova-cien-design.md`.
Postup: inline, každý krok najprv test (TDD), na konci celé testy a nezávislá
kontrola.

## Global Constraints

- Predvolený čas je 07:00, predvolený počet 80, najviac 100 (`MAX_REFRESH_LIMIT`).
- Bez schopnosti `brickeconomy.prices` sa nič nevolá a prepínač je zakázaný.
- Čas sa zadáva cez `v-time-picker` z Vuetify v obale `TimeField.vue`, nie
  cez `type="time"`.
- Jeden proces nad SQLite: zámok `DataDir.lock`.
- Texty pre používateľa sú bez slova „appka“. Množné číslo má tri tvary.
- Commity ako `jakubmatisak <jakubmatisak@users.noreply.github.com>`.

## Úlohy

1. **`services/auto_refresh.py`:**
   - `AutoPrefs`, `prefs_of(user)` s predvolenými hodnotami a kontrolou rozsahu;
   - `due_users(session, settings, now)`;
   - `run_due(sessionmaker, settings, now, should_stop, provider_for)`;
   - záznam `auto_refresh_last` v `app_settings`, `last_run(session, user_id)`;
   - `earliest_time(session)` a háčik `on_schedule_change`.
   - V `refresh_prices` pribudne `should_stop`, v `_DailyQuota` metóda `seed`.
   - Testy: `tests/test_auto_refresh.py`.
2. **API:**
   - `autoRefresh` do `PREFERENCE_KEYS` s kontrolou;
   - po uložení preferencií sa zavolá synchronizácia plánu;
   - `RefreshStatusOut.auto_last`;
   - testy.
3. **Plánovač v otvorenej aplikácii:**
   - nastavenie `auto_refresh_scheduler` (desktop ho zapne v
     `DataDir.environment`);
   - v lifespan beží slučka raz za minútu cez `run_due`;
   - test s krátkou slučkou.
4. **`lego_desktop/scheduler.py`:**
   - XML úlohy, `apply(time | None)` cez `schtasks` (`subprocess`, bez okna);
   - testy XML a príkazov.
5. **`lego_desktop/main.py`:**
   - `--refresh-prices` (zámok, prostredie, migrácie, `run_due`, značky
     `.running` a `.stop`);
   - bežný štart pri bežiacom behu pošle stop a čaká 30 s;
   - registrácia háčika plánu a synchronizácia pri štarte;
   - testy.
6. **Inštalátor:** `[UninstallRun]` zmaže úlohu; test v `test_installer.py`.
7. **Frontend:**
   - `TimeField.vue` (`v-time-picker`);
   - sekcia na karte BrickEconomy (len desktop): prepínač, čas, počet,
     riadok posledného behu;
   - tooltip tlačidla v lište;
   - testy.
8. **Zásady, CLAUDE.md, README:**
   - riadok o úlohe Plánovača, `privacy_version`;
   - zmenené pravidlo obnovy;
   - počty testov.

## Review Focus

- Účet bez kľúča alebo s vypnutou schopnosťou sa nesmie obnoviť ani vtedy,
  keď má `autoRefresh.enabled`.
- Dva behy v ten istý deň: druhý beh obnovu nespustí, len prerušený beh dobehne.
- Kvóta: beh neminie viac než `limit` ani než zvyšok dňa, aj po reštarte
  procesu (počítadlo sa naplní z `api_calls`).
- Čas z nastavení sa porovnáva s miestnym časom počítača, nie s UTC.
- Zlyhanie `schtasks` (napríklad vypnutý Plánovač) nesmie zhodiť uloženie
  nastavení. Chyba ide do logu a rozhranie ju ukáže.
