# Moje kocky Desktop

Evidencia zbierky LEGO® setov ako **bežná inštalácia pre Windows**. Je to tá
istá appka ako webová [Moje kocky](https://github.com/jakubmatisak/lego-app),
len beží v okne na tvojom počítači: bez servera, bez Dockeru a **bez
otvoreného portu**. Všetky údaje (zbierka, fotky, kľúče) ostávajú u teba
v `%APPDATA%\MojeKocky`.

![Prehľad: hodnota portfólia, zisk a rozdelenie podľa sérií](docs/screenshots/prehlad.png)

*Snímka je z webovej verzie, desktop vyzerá rovnako.*


## Čo to vie

**Evidencia**

- **Po kusoch.** Tri rovnaké sety sú tri záznamy, každý s vlastným stavom
  (v krabici, postavený, rozobratý…), cenou, dátumom a umiestnením.
- **Umiestnenie v dvoch úrovniach**: miestnosť a číslo krabice, s našepkávačom.
- **Mám to už?** Pri zadaní čísla sa ukáže výrazný pás, keď set v zbierke je.
- **Zberateľské minifigúrky.** Séria sa pridáva výberom z mriežky figúrok,
  nerozbalený sáčok sa po rozbalení priradí ku konkrétnej figúrke. Sekcia
  Figúrky pozná všetky série, aj nezačaté, a ukáže, čo chýba. Rovnako
  blind-box série iných radov (Mighty Machines, Super Mario a pod.).
- **Série a vlny.** Koľko setov z témy a roku máš, podľa zoznamu Brickset.
- **Vlastné kategórie** s pravidlami (napr. všetko s „F1“ v názve naprieč
  sériami) aj ručným zaradením.
- **Chcem**: zoznam želaných setov s cieľovou cenou a poznámkou. Set, ktorý na
  cieľ klesol, sa zvýrazní. „Kúpil som“ ho presunie do zbierky.
- **Vlastné fotky kusu** a **súpis pre poistku** na tlač alebo do PDF.
- **Galéria ďalších oficiálnych fotiek setu** z Brickset (dá sa vypnúť).

**Pridávanie**

- **Čítačka čiarových kódov** (USB, v režime klávesnice) aj **kamera** v
  prehliadači. Sken funguje z ktorejkoľvek obrazovky. Rovnaký kód zvýši
  počet, iný kód uloží rozpracovaný set a načíta nový; každé uloženie sa dá
  vrátiť tlačidlom Späť.
- **Pamäť formulára**: stav, dátum a umiestnenie z minulého setu sa predvyplnia.
- **Hromadný import** z Excelu alebo CSV so šablónou, náhľadom a vrátením.
  Export do CSV.
- **Bez kľúča Rebrickable** sa set dá uložiť ručne, len číslom.

**Peniaze**

- **Dva druhy zisku oddelene.** Nerealizovaný (trhová hodnota mínus kúpna
  cena toho, čo vlastníš) a realizovaný (čistý z predajov, po poplatkoch
  a poštovnom). Nikdy sa nesčítajú do jedného čísla.
- **Ročný výnos** kusu, série, zoznamu aj celej zbierky, od roka držania.
- **V dnešných peniazoch**: prepočet kúpnych cien infláciou (HICP Slovensko).
- **Odhad hodnoty** kusov v krabici o 2 a 5 rokov.
- **Kto sa hýbe**: zmena trhovej ceny za 30, 90 a 365 dní.
- **Overiť cenu**: v obchode naskenuješ krabicu a hneď vidíš, čo to je, či to
  máš, cenu nového aj použitého kusu a graf histórie. Overené sety sa
  pamätajú v tabuľke.
- **Návrh ceny a text inzerátu** pre Aukro alebo Bazoš.
- **Skryť ceny** jedným klikom, keď niekomu ukazuješ portfólio.

**Prehľad a zoznamy**

- Filtre, ktoré sa skladajú (v skupine ALEBO, medzi skupinami A), hľadanie
  bez diakritiky, desať spôsobov zoradenia, uložené pohľady, karty alebo
  tabuľka, hromadná úprava vybraných kusov.
- Prehľad sa dá zúžiť na sériu, kategóriu alebo uložený pohľad.

**Ostatné**

- Viac účtov na jednom počítači (napríklad pre členov rodiny), každý so
  svojou zbierkou, heslom a kľúčmi. Ďalší účet povolí prvý (správca)
  v Nastaveniach → Aplikácia.
- Rozhranie po slovensky aj po anglicky, svetlý a tmavý režim, telefón aj
  počítač. Nastavenia zobrazenia sa pamätajú pri účte.
- Prehľad spotreby volaní cudzích služieb a prepínače, čo sa z ktorej
  služby smie sťahovať.

## Inštalácia

1. Stiahni `MojeKocky-Setup-x.y.z.exe` z [Releases](../../releases).
2. Spusti ho. Inštaluje sa len pre teba, práva správcu netreba.
   Inštalátor nie je podpísaný, Windows preto raz ukáže „Windows chránil
   tento počítač“: klikni **Ďalšie informácie → Spustiť aj tak**.
3. Pri prvom spustení si vytvoríš účet s heslom. Pri ďalších sa pýta heslo.

Potrebuje Windows 10 alebo 11 (64-bit) a Microsoft Edge WebView2, ktorý
v nich býva. Ak chýba, inštalátor ponúkne stránku na jeho stiahnutie.

**Údaje** sú v `%APPDATA%\MojeKocky`: `lego.db` (databáza), `photos\`,
`secret.key` (šifruje uložené kľúče k službám) a `logs\`. **Záloha** je kópia
celého priečinka. Nová verzia sa nainštaluje cez starú a údaje ostanú.
Odinštalovanie sa opýta, či ich zmazať.

Ako to funguje bez servera: okno (pywebview nad WebView2) načíta stránku
zo súborov a každé volanie appky pošle priamo Pythonu v tom istom procese
(most `window.pywebview.api` → FastAPI cez `httpx.ASGITransport`). Na
žiadnom porte nič nepočúva.

## Kľúče k službám

Appka funguje aj bez kľúčov; vtedy je to evidencia, kde si názov setu a cenu
vyplníš sám. Každá služba pridá niečo navyše.

Kľúče vložíš v appke v **Nastaveniach → Dáta**. Kde nejaký kľúč chýba,
appka to povie priamo pri údaji (a na Prehľade v karte „Čo ešte appka vie“)
aj s odkazom na pripojenie. Kľúče sú uložené zašifrované v databáze na tomto
počítači a rozhranie ukáže len ich koncovku. Šifruje ich súbor
`%APPDATA%\MojeKocky\secret.key`: keby sa stratil, zbierka ostane, len
kľúče treba zadať znova.

| Služba | Na čo je | Cena a limit | Kľúč |
|---|---|---|---|
| [Rebrickable](https://rebrickable.com/api/) | názvy, roky, dieliky, fotky, série, figúrky | zdarma, ~1 volanie/s | nastavenia účtu na rebrickable.com |
| [Brickset](https://brickset.com/article/52664/api-version-3-documentation) | pôvodná cena, čiarové kódy, popis, štítky, vlny sérií, ďalšie fotky setu | zdarma, 100 volaní/deň | [žiadosť o kľúč](https://brickset.com/tools/webservices/requestkey) |
| [BrickEconomy](https://www.brickeconomy.com/api-reference) | trhová cena nového a použitého kusu, história, odhady | súčasť Premium, 100 volaní/deň | profil na brickeconomy.com |
| [UPCitemdb](https://www.upcitemdb.com/) | záložné hľadanie podľa čiarového kódu | zdarma, bez kľúča, ~100 dotazov/deň na IP adresu | netreba, zapína sa v Nastaveniach |
| [Eurostat](https://ec.europa.eu/eurostat/) | inflácia pre prepočet do dnešných peňazí | zdarma, bez kľúča | netreba, zapína sa v Nastaveniach |

### Ako sa šetria volania

Nič sa nedeje samo od seba, nie je tu plánovač. Obnovu cien spúšťa tlačidlo
v hornej lište a beží na pozadí. Denná kvóta BrickEconomy je 100 volaní,
preto:

1. Hromadná obnova neťahá ceny mladšie než týždeň.
2. Na jedno spustenie najviac 40 položiek, od najstaršej; zvyšok pri
   ďalšom (dávka sa dá zmeniť na karte BrickEconomy).
3. Platí zvyšok dennej kvóty, po odpovedi 429 sa dávka zastaví.
4. Jedno volanie na set: odpoveď nesie cenu nového aj použitého kusu
   a históriu, takže nový aj postavený kus sa obnovia spolu.
5. Overiť cenu nepýta cenu, ktorá je mladšia než 24 hodín.

História cien príde v tej istej odpovedi, graf a „Kto sa hýbe“ teda majú čo
ukazovať hneď po pridaní setu. Brickset a Rebrickable majú v Nastaveniach
vlastné prepínače a rezervu, aby dopĺňanie na pozadí nezjedlo limit
potrebný na pridávanie.

## Vývoj

Potrebuješ Python 3.13 (cez [uv](https://docs.astral.sh/uv/)) a Node 22.

```powershell
cd frontend; npm ci; npm run build-desktop
cd ..\backend; uv sync; uv run moje-kocky
```

`build-desktop` zostaví frontend do `frontend/dist-desktop` (relatívne cesty,
navigácia za `#`, fetch cez most). Testy:

```powershell
cd backend; uv run pytest; uv run ruff check src tests
cd ..\frontend; npm run type-check; npm run lint; npm test
```

### Zostavenie inštalátora

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -Version 0.1.0
```

Frontend → PyInstaller (`packaging/moje-kocky.spec`, výsledok
`build/dist/MojeKocky/MojeKocky.exe`) → Inno Setup (`packaging/moje-kocky.iss`,
výsledok `build/installer/MojeKocky-Setup-0.1.0.exe`). Bez nainštalovaného
Inno Setup skript skončí pri programe. Na GitHube zostaví inštalátor
workflow `release` pri každom tagu `v*` a priloží ho k Release.

```
backend/src/lego_api/      appka (FastAPI, SQLAlchemy 2, SQLite, Alembic)
backend/src/lego_desktop/  okno, most, %APPDATA%, zámok jednej inštancie
frontend/                  Vue 3, Vuetify 4; src/desktop/ = fetch cez most
packaging/                 PyInstaller, Inno Setup, ikona
scripts/build.ps1          celé zostavenie
```

## Zdroje dát a poďakovanie

Moje kocky je nezávislý projekt fanúšika. Nie je spojený so skupinou LEGO
Group ani s nižšie uvedenými službami a nie je nimi sponzorovaný ani schválený.

LEGO® je ochranná známka skupiny spoločností LEGO Group, ktorá tento projekt
nesponzoruje, neautorizuje ani neschvaľuje. *(LEGO® is a trademark of the LEGO
Group of companies which does not sponsor, authorize or endorse this site.)*
Obrázky setov a minifigúrok sú chránené autorským právom LEGO Group
a zobrazujú sa len na nekomerčné informačné účely v súlade s pravidlami
[LEGO Fair Play](https://www.lego.com/en-us/legal/notices-and-policies/fair-play).

- **Katalóg setov, minifigúrok a obrázky:** [Rebrickable](https://rebrickable.com),
  cez [Rebrickable API](https://rebrickable.com/api/).
- **Pôvodné ceny, čiarové kódy, popisy, série, vlny a ďalšie fotky setov:**
  [Brickset](https://brickset.com), cez Brickset API v3. Image(s) courtesy of Brickset.com.
- **Trhové ceny a odhady hodnoty:** [BrickEconomy](https://www.brickeconomy.com),
  len pre používateľov s vlastným kľúčom BrickEconomy Premium. Ceny sú odhady
  BrickEconomy, nie investičné poradenstvo.
- **Vyhľadanie podľa čiarového kódu (záložné):** [UPCitemdb](https://www.upcitemdb.com).
- **Inflácia (HICP Slovensko):** Zdroj: Eurostat, dátový súbor
  [prc_hicp_minr](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table).
  Appka z indexu počíta prepočet cien do dnešných peňazí; je to úprava dát,
  za ktorú Eurostat nezodpovedá
  ([podmienky opätovného použitia](https://ec.europa.eu/eurostat/help/copyright-notice)).

Kľúče k službám patria jednotlivým používateľom a ich použitie sa riadi
podmienkami danej služby.

### Softvér tretích strán

Backend: [FastAPI](https://fastapi.tiangolo.com), [SQLAlchemy](https://www.sqlalchemy.org),
[Alembic](https://alembic.sqlalchemy.org), [Pydantic](https://docs.pydantic.dev),
[Uvicorn](https://www.uvicorn.org), [HTTPX](https://www.python-httpx.org),
[argon2-cffi](https://argon2-cffi.readthedocs.io), [PyJWT](https://pyjwt.readthedocs.io),
[cryptography](https://cryptography.io), [openpyxl](https://openpyxl.readthedocs.io)
a ďalšie (MIT, BSD, Apache-2.0).

Frontend: [Vue](https://vuejs.org), [Vuetify](https://vuetifyjs.com),
[Pinia](https://pinia.vuejs.org), [Vue Router](https://router.vuejs.org),
[vue-i18n](https://vue-i18n.intlify.dev), [VueUse](https://vueuse.org),
[Chart.js](https://www.chartjs.org) s [vue-chartjs](https://vue-chartjs.org)
a chartjs-plugin-zoom, [openapi-fetch](https://openapi-ts.dev) (MIT);
čítanie kódov [ZXing-C++](https://github.com/zxing-cpp/zxing-cpp) cez
[zxing-wasm](https://github.com/Sec-ant/zxing-wasm) (Apache-2.0, MIT, BSD-3-Clause);
ikony [Material Design Icons](https://pictogrammers.com/library/mdi/) (Apache-2.0);
písmo [Roboto](https://github.com/googlefonts/roboto-classic) (SIL Open Font License 1.1).

Žiadna závislosť nie je pod GPL, AGPL ani LGPL.

## Licencia

Zdrojový kód je pod licenciou [MIT](LICENSE). Licencia sa nevzťahuje na dáta,
ceny a obrázky zo služieb tretích strán ani na ochrannú známku LEGO® a obrázky
výrobkov LEGO; tie patria svojim vlastníkom.

## Súkromie a licencie

Nie je to právna rada, len to, ako desktopová appka rieši súkromie
a podmienky služieb (k septembru 2026).

- **Údaje sú len na tvojom počítači** v `%APPDATA%\MojeKocky`. Appka nemá
  server ani prevádzkovateľa, autor k nim nemá prístup. Ide o osobné použitie
  v domácnosti, na ktoré sa GDPR nevzťahuje (čl. 2 ods. 2 písm. c).
- **Čo odchádza z počítača:** len otázky na služby, ktoré si pripojíš
  (čísla setov a čiarové kódy pod tvojím kľúčom), stiahnutie indexu inflácie
  z Eurostatu (keď ho zapneš) a obrázky setov, ktoré sa načítavajú priamo
  z Rebrickable a Brickset (tie vidia IP adresu počítača).
- **Kým účet nezadá vlastný kľúč, zo služby nevidí nič.** Pri viacerých
  účtoch na jednom počítači vidí každý len to, čo stiahol jeho vlastný kľúč.
- **Tvoje práva a kontrola:** v Nastaveniach → Účet si stiahneš všetky svoje
  údaje (ZIP) alebo zmažeš účet. Odinštalovanie sa opýta, či zmazať aj
  priečinok s údajmi.
- **Fotky** sa ukladajú zmenšené a bez polohy GPS.
- **Cookies ani sledovanie** appka nepoužíva. Okno si pamätá len nastavenia
  zobrazenia (tmavý režim, skryté ceny a pod.).
- **Služby:** Rebrickable dovoľuje akékoľvek použitie; BrickEconomy a
  Brickset dávajú osobné licencie ku kľúču, preto ich údaje vidí len účet
  s vlastným kľúčom. Ak svoj kľúč BrickEconomy vložíš do viacerých účtov,
  zdieľaš licenciu.
- **Nekomerčne:** pravidlá LEGO Fair Play aj licencia BrickEconomy platia
  len pre osobné, nekomerčné použitie. Logo LEGO appka nepoužíva.
