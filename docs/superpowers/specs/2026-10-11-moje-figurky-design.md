# Moje figúrky: jednotlivé kusy figúrok s filtrami a hodnotou

Dátum: 2026-10-11. Stav: návrh na schválenie.

## Prečo

Figúrky dnes ukazujú len zoznam sérií a v sérii, ktoré figúrky mám. Chýba:

1. **Hodnota mojich figúrok** ako v Zbierke: riadok Kúpené · Hodnota · Zisk.
2. **Filtre ako v Zbierke**, hlavne Umiestnenie a Krabica. Keď figúrku
   uložím do krabice, nemám kde zistiť, kde je, ani čo je v krabici 3.

Zbierka figúrky zo sérií zámerne neukazuje (`sets_only`), takže filter
Krabica v nej figúrky nenájde, len na ne odkáže (`FiguresElsewhere`).

## Čo vznikne

Vo Figúrkach prepínač **Série / Moje figúrky** (na mieste kariet kategórií,
nad nimi). Moje figúrky sú nová trasa `figurky/kusy` (`minifig-pieces`),
ktorá použije tú istú obrazovku ako Zbierka (`CollectionView`), len
s rozsahom „figúrky zo sérií“:

- karty aj tabuľka, „Sety spolu“ (tu jedna figúrka spolu) a „Jednotlivé kusy“,
  Vlastnené / Predané / Všetko, zoradenie, hľadanie;
- celý panel filtrov zo Zbierky (Umiestnenie, Krabica, Stav, Séria,
  kúpna cena a dátum, kategórie, …) s počtami, ktoré platia pre figúrky;
- riadok súčtov Kúpené · Hodnota · Zisk podľa filtra (`FacetsOut.totals`),
  teda požiadavka 1 bez novej logiky;
- výber na úpravu a hromadná úprava (napríklad presun do inej krabice),
  rovnaký výber ako v Zbierke;
- úzka tabuľka s kompaktným riadkom ako v Zbierke.

Nerozbalené sáčky sú tiež kusy figúrok zo sérií, v Moje figúrky budú tiež
(štítok sáčok už karta má). Klik na figúrku vedie na jej detail
s `?from=minifigs`, ponuka svieti na Figúrkach.

## Server

- `ItemFilter.figures_only` (query `figures_only`), zrkadlo `sets_only`:
  `in_section` vráti len figúrky zo sérií (`kind_of == "minifig"`).
  Oba naraz nedávajú zmysel, platí `sets_only`.
- Ide cez `FilterDep`, takže `/items`, `/items/grouped`, `/items/facets`,
  `/items/bulk-update` a súčty ho dostanú samy. `hidden_figures` ostáva len
  pre `sets_only`.
- Ponuka volieb v paneli (`universe`) sa ráta z rozsahu sekcie, takže
  v Moje figúrky nebudú témy či podtémy, ktoré majú len sety. Umiestnenie
  a Krabica ostávajú zo všetkých kusov, ako v Zbierke.

## Frontend

- `filterStore` dostane sekciu (`sets` | `figures`); `sectionQuery()` pošle
  `sets_only` alebo `figures_only`. Filtre sa pri zmene sekcie vymenia,
  každá sekcia má svoje.
- `CollectionView` dostane prop `section`. Pre `figures`:
  - pamäť filtra a pohľadu pri účte pod kľúčom `figures`, nie `collection`;
  - hlavička počíta figúrky (z `FacetsOut.totals`), nie `collection_*_count`;
  - bez tlačidla Pridať set (figúrky sa pridávajú v sérii), bez riadku
    `FiguresElsewhere` a bez presmerovania figúrkových filtrov do Figúrok
    (`hasStaleKeys`, `figuresRoute` platia len pre Zbierku);
  - uložené pohľady zatiaľ len v Zbierke (v Moje figúrky skryté).
- `stores/collection.ts` načíta zoznam podľa sekcie; pri prepnutí sekcie
  začne kostrou (iný obsah na tej istej obrazovke).
- Zoznam sérií (`MinifigsView`) dostane prepínač Série / Moje figúrky; trasa
  Moje figúrky ho má tiež, na rovnakom mieste.

## Čo sa nemení

- Zbierka ostáva len so setmi, Prehľad, export a súpis počítajú všetko.
- Žiadne volanie von, žiadna nová tabuľka ani migrácia.

## Testy

- Server: `figures_only` vráti len figúrky (aj sáčky), počty a súčty platia
  pre ne, filter Krabica nájde figúrku v krabici, `sets_only` sa nezmenil.
- Frontend: `sectionQuery` podľa sekcie, pamäť pod kľúčom `figures`, Moje
  figúrky bez Pridať set a bez `FiguresElsewhere`, prepínač vo Figúrkach.
- Na kópii databázy (:8001): filter Krabica nájde figúrku, súčty sedia
  so súčtom kariet sérií (`SeriesValueCard`).

## Zamietnuté

- Len filter miesta v zozname sérií: menšie, ale bez ostatných filtrov
  a bez riadku súčtov (používateľ zvolil Moje figúrky).
- Vlastná kópia Zbierky pre figúrky: dva zoznamy by sa rozišli, ako kedysi
  zoskupený zoznam a filtre.
