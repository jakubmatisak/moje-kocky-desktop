# Cena celej série a chýbajúcich figúrok

Dátum: 2026-10-26. Stav: hotové (web).

## Prečo

Keď niekto ponúkne figúrky alebo celú sériu, treba rýchlo vedieť, či je cena
dobrá. Doteraz sa dala zistiť cena každej chýbajúcej figúrky len zvlášť
(Obnoviť cenu v detaile) a súčet aj vývoj v čase chýbal. Ponúkajú sa nové
figúrky, preto sa ráta s cenou nového kusu.

## Čo používateľ vidí

**Stránka série vo Figúrkach** (`SeriesValueCard.vue`):

- Karta sa ukáže aj pri sérii, z ktorej nemám nič (titul „Cena série“),
  keď séria má v katalógu členov.
- **Chýba mi:** súčet cien figúrok, ktoré nemám, zelenou (len keď niečo mám).
- **Celá séria:** každá figúrka raz, zelenou. Keď niektorá cenu nemá,
  „bez ceny: N figúrok“ a súčet je len z tých, ktoré ju majú.
- V grafe zelená čiarkovaná čiara **Celá séria** (súčet histórie cien
  figúrok, ktoré cenu majú; pred prvou cenou figúrky jej prvá cena). Pri
  neúplnej sérii legenda „Celá séria (11 z 12)“. Figúrka bez ceny chýba
  v súčte celý čas, takže súčet neklesne ani neposkočí. (Pôvodne len pri
  všetkých cenách; 11 z 12 aj séria bez mojich figúrok potom nemali graf.)
- Tlačidlo **Zistiť ceny chýbajúcich** (s kľúčom BrickEconomy a keď niečo
  chýba): najprv povie, koľko volaní to stojí a koľko dnes ostáva, stiahne
  až po potvrdení. Keď sú všetky ceny aktuálne, nevolá nič a povie to.
  Po stiahnutí sa načíta karta aj karty figúrok (ceny pri chýbajúcich).

**Zoznam sérií:** stĺpec Celá séria (radí sa) a riadok na karte, len
z cien, ktoré už sú v databáze. Zoznam sám nič nesťahuje.

## Pravidlá

- Nič automaticky. Hromadná ani automatická obnova chýbajúce figúrky
  nepýta; Zistiť ceny chýbajúcich je ručná akcia.
- Cena mladšia než `price_max_age_hours` (15 dní) je aktuálna a nepýta sa
  znova (rozhodnutie používateľa). Platí aj pre moje figúrky v tej istej
  dávke.
- Jedno volanie na figúrku: cieľ je set pod číslom figúrky, nový kus
  (`PriceTarget(num, SET, NEW)`), rovnako ako `figure_values.market_now`.
  Odpoveď prinesie aj históriu, graf je hneď celý.
- Strop dávky, zvyšok kvóty, rezerva a zámok proti súbehu platia ako pri
  inej obnove.

## Ako

- `series_value.py::_whole_series`: členovia série (len s kľúčom
  Rebrickable, ako `members_of`), `missing_*`, `series_*`, `history_all`
  cez spoločné jadro `_sum_history`.
- `refresh.collect_targets(..., whole_series=True)` s číslom série v `only`
  pridá každého člena; `refresh_prices` a `POST /prices/refresh-all`
  prijmú `whole_series` (vtedy bez `force`).
- `GET /prices/series/{num}/refresh-plan` → `calls`, `fresh`,
  `max_age_days`; von nevolá.
- `cmf.overview` pridá `series_total` a `series_priced` z
  `figure_values.market_now`.
- Frontend: `PriceHistoryChart` prop `wholePoints`, farba
  `CHART_COLORS.whole`; `prices.refreshOne(num, done, wholeSeries)`;
  `seriesList` kľúče `wholeDesc`/`wholeAsc`.
