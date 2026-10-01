<script setup lang="ts">
  /**
   * Zásady ochrany súkromia (GDPR, čl. 13). Verejná stránka, bez prihlásenia.
   *
   * Prevádzkovateľa (meno a kontakt) vyplní správca v Nastaveniach →
   * Aplikácia. Text zodpovedá tomu, čo appka naozaj robí: pri zmene
   * spracúvania treba upraviť text aj `privacy_version` na serveri.
   */
  import { computed, onMounted } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { isDesktop } from '@/desktop/bridge'
  import { useAuthStore } from '@/stores/auth'

  interface Section { title: string, body: string[] }

  const { locale, t } = useI18n()
  const auth = useAuthStore()

  onMounted(() => {
    auth.loadProviders()
  })

  const operatorName = computed(() => auth.providers?.operator_name ?? null)
  const operatorEmail = computed(() => auth.providers?.operator_email ?? null)
  const version = computed(() => auth.providers?.privacy_version ?? '')

  const SK: Section[] = [
    {
      title: 'Aké údaje spracúvame',
      body: [
        'Údaje účtu: e-mail, meno (ak ho zadáš), heslo uložené len ako odtlačok (argon2), jazyk a nastavenia zobrazenia.',
        'Tvoja zbierka: kusy, kúpne a predajné ceny, dátumy, umiestnenie, poznámky, zoznam Chcem, kategórie, uložené pohľady, odkazy na pozretie, overené ceny a ručne zadané ceny.',
        'Tvoje fotky kusov. Pri nahratí sa zmenšia a zmažú sa z nich údaje fotoaparátu vrátane polohy GPS.',
        'Kľúče k službám, ktoré si sám vložíš (Rebrickable, Brickset, BrickEconomy). Ukladajú sa zašifrované a nikdy sa nezobrazia celé.',
        'Záznam volaní cudzích služieb (čo, kedy, s akým výsledkom) 30 dní a prihlasovacie tokeny najviac 30 dní (pozri Ako dlho).',
      ],
    },
    {
      title: 'Prečo a na akom základe',
      body: [
        'Aby sa dala viesť tvoja evidencia: plnenie zmluvy, čl. 6 ods. 1 písm. b GDPR.',
        'Záznam volaní a tokeny kvôli bezpečnosti a stráženiu denných limitov služieb: oprávnený záujem, čl. 6 ods. 1 písm. f GDPR.',
        'Moje kocky nepoužívajú reklamu, analytiku ani sledovanie a údaje nepredávajú.',
      ],
    },
    {
      title: 'Ako dlho',
      body: [
        'Údaje účtu a zbierky, kým účet nezmažeš. Záznam volaní 30 dní.',
        'Prihlásenie do zatvorenia prehliadača, na serveri najviac 12 hodín bez použitia. Keď pri prihlásení zaškrtneš Zapamätať si prihlásenie, 30 dní od posledného použitia. Odhlásenie ho zruší hneď.',
        'Pred každou aktualizáciou na inú verziu sa celá databáza zálohuje na server do priečinka backups. Uchováva sa 5 posledných záloh, staršie sa mažú, a zálohu staršiu než 90 dní zmaže najbližší štart. Rovnako sa maže aj databáza, ktorú správca pri návrate zálohy odloží do toho istého priečinka. Údaje zmazaného účtu v nich môžu ostať, kým sa zálohy neprestriedajú, najdlhšie do prvého štartu Mojich kociek po 90 dňoch.',
      ],
    },
    {
      title: 'Kto ich dostane',
      body: [
        isDesktop
          ? String.raw`Nikto: v desktopovej verzii sú všetky údaje len na tomto počítači, v priečinku %APPDATA%\MojeKocky.`
          : 'Poskytovateľ hostingu, na ktorom Moje kocky bežia.',
        'Služby, ktoré si pripojíš vlastným kľúčom, dostanú len čísla setov a čiarové kódy, na ktoré sa pýtaš, nie tvoje osobné údaje. Eurostat nedostane nič, čo by sa ťa týkalo.',
        'Pri inej mene zobrazenia než euro alebo pri sume v cudzej mene stiahne server kurzy z Európskej centrálnej banky (ECB). Sťahujú sa len verejné kurzy, o tebe neodchádza nič.',
        isDesktop
          ? 'Fotky setov sa načítavajú priamo z Rebrickable a Brickset, tie vidia IP adresu tohto počítača.'
          : 'Fotky setov sa načítavajú cez server tejto inštancie, takže Rebrickable ani Brickset nevidia tvoju IP adresu.',
      ],
    },
    {
      title: 'Tvoje práva',
      body: [
        'Prístup a prenosnosť: v Nastaveniach → Účet si stiahneš všetky svoje údaje aj fotky (ZIP).',
        'Oprava: údaje zmeníš priamo v Mojich kockách.',
        'Vymazanie: v Nastaveniach → Účet zmažeš účet so všetkým, čo k nemu patrí. V zálohách pred aktualizáciou ostane, kým sa neprestriedajú, najdlhšie do prvého štartu Mojich kociek po 90 dňoch (pozri Ako dlho).',
        'Námietka a obmedzenie spracúvania: napíš prevádzkovateľovi.',
        'Sťažnosť: Úrad na ochranu osobných údajov Slovenskej republiky, dataprotection.gov.sk.',
      ],
    },
  ]

  const EN: Section[] = [
    {
      title: 'What data we process',
      body: [
        'Account data: e-mail, name (if you enter it), password stored only as a hash (argon2), language and display settings.',
        'Your collection: pieces, purchase and sale prices, dates, location, notes, wishlist, categories, saved views, share links, price checks and manually entered prices.',
        'Your photos of pieces. On upload they are shrunk and camera data including the GPS location is removed.',
        'Keys to services you add yourself (Rebrickable, Brickset, BrickEconomy). They are stored encrypted and never shown in full.',
        'A log of calls to external services (what, when, with what result) for 30 days and sign-in tokens for at most 30 days (see How long).',
      ],
    },
    {
      title: 'Why and on what basis',
      body: [
        'To keep your records: performance of a contract, Art. 6(1)(b) GDPR.',
        'The call log and tokens for security and to respect the services’ daily limits: legitimate interest, Art. 6(1)(f) GDPR.',
        'The app uses no advertising, analytics or tracking and does not sell data.',
      ],
    },
    {
      title: 'How long',
      body: [
        'Account and collection data until you delete the account. Call log 30 days.',
        'Sign-in until you close the browser, on the server at most 12 hours without use. If you tick Remember me when signing in, 30 days since last use. Signing out ends it at once.',
        'Before every update of the app to another version, the whole database is backed up on the server to the backups folder. The last 5 backups are kept, older ones are deleted, and the app deletes a backup older than 90 days the next time it starts. The same applies to the database the operator sets aside in that folder when restoring a backup. Data of a deleted account may remain in them until the backups rotate out, at the longest until the first start of the app after 90 days.',
      ],
    },
    {
      title: 'Who receives it',
      body: [
        isDesktop
          ? String.raw`Nobody: the desktop app keeps all data on this computer only, in %APPDATA%\MojeKocky.`
          : 'The hosting provider the app runs on.',
        'Services you connect with your own key receive only the set numbers and barcodes you ask about, not your personal data. Eurostat receives nothing about you.',
        'With a display currency other than the euro, or an amount in a foreign currency, the server downloads exchange rates from the European Central Bank (ECB). Only the public rates are downloaded, nothing about you is sent.',
        isDesktop
          ? 'Set pictures are loaded directly from Rebrickable and Brickset, which see this computer’s IP address.'
          : 'Set pictures are loaded through the app’s server, so Rebrickable and Brickset do not see your IP address.',
      ],
    },
    {
      title: 'Your rights',
      body: [
        'Access and portability: in Settings → Account you download all your data and photos (ZIP).',
        'Rectification: change your data directly in the app.',
        'Erasure: in Settings → Account you delete the account with everything that belongs to it. It stays in the pre-update backups until they rotate out, at the longest until the first start of the app after 90 days (see How long).',
        'Objection and restriction: write to the operator.',
        'Complaint: the Office for Personal Data Protection of the Slovak Republic, dataprotection.gov.sk.',
      ],
    },
  ]

  /** Desktop: bez servera a prevádzkovateľa, všetko na tomto počítači. */
  const SK_DESKTOP: Section[] = [
    {
      title: 'Kde sú tvoje údaje',
      body: [
        String.raw`Všetko je len na tomto počítači v priečinku %APPDATA%\MojeKocky: databáza a jej zálohy, fotky, zašifrované kľúče, zapamätané prihlásenie (ak si ho zvolíš) a denník. Moje kocky nemajú server ani prevádzkovateľa a autor k údajom nemá prístup.`,
        'Ide o osobné použitie v domácnosti; na také spracúvanie sa GDPR nevzťahuje (čl. 2 ods. 2 písm. c). Ak Moje kocky na počítači používa viac ľudí, každý má svoj účet s heslom.',
      ],
    },
    {
      title: 'Čo sa ukladá',
      body: [
        'Účet: meno, e-mail (ak ho zadáš), heslo len ako odtlačok (argon2), jazyk a nastavenia zobrazenia.',
        'Zbierku: kusy, ceny, dátumy, umiestnenie, poznámky, Chcem, kategórie, uložené pohľady, overené a ručne zadané ceny.',
        'Fotky kusov, zmenšené a bez údajov fotoaparátu vrátane polohy GPS.',
        'Kľúče k službám zašifrované súborom secret.key a záznam volaní služieb za posledných 30 dní.',
        String.raw`Keď pri prihlásení zaškrtneš Zapamätať si prihlásenie, prihlasovací token v súbore %APPDATA%\MojeKocky\session.bin, zašifrovaný súborom secret.key. Platí 30 dní od posledného použitia a zmaže ho odhlásenie aj zmazanie účtu. Zmena hesla ho vymení za nový a ostatné prihlásenia účtu zruší. Bez zaškrtnutia je prihlásenie len v pamäti, kým je okno otvorené, najviac 12 hodín bez použitia.`,
        String.raw`Pred každou aktualizáciou na inú verziu kópiu celej databázy v priečinku %APPDATA%\MojeKocky\backups. Uchováva sa 5 posledných záloh, staršie sa mažú, a zálohu staršiu než 90 dní zmaže najbližší štart. Údaje zmazaného účtu v nich môžu ostať, kým sa zálohy neprestriedajú, najdlhšie do prvého štartu Mojich kociek po 90 dňoch.`,
      ],
    },
    {
      title: 'Čo odchádza z počítača',
      body: [
        'Len otázky na služby, ktoré si sám pripojíš (Rebrickable, Brickset, BrickEconomy, UPCitemdb): čísla setov a čiarové kódy pod tvojím vlastným kľúčom. Osobné údaje nie.',
        'Index inflácie z Eurostatu, keď prepočet do dnešných peňazí zapneš. Eurostat nedostane nič o tebe.',
        'Kurzy z Európskej centrálnej banky (ECB), keď zvolíš inú menu zobrazenia než euro alebo zadáš sumu v cudzej mene. Sťahujú sa len verejné kurzy, o tebe neodchádza nič.',
        'Obrázky setov sa načítavajú priamo z Rebrickable a Brickset, tie vidia IP adresu tohto počítača.',
      ],
    },
    {
      title: 'Tvoja kontrola',
      body: [
        'V Nastaveniach → Účet si stiahneš všetky svoje údaje (ZIP) alebo zmažeš účet so všetkým, čo k nemu patrí. V zálohách pred aktualizáciou ostane, kým sa neprestriedajú, najdlhšie do prvého štartu Mojich kociek po 90 dňoch.',
        String.raw`Odinštalovanie sa opýta, či zmazať aj priečinok s údajmi účtu Windows, pod ktorým odinštalovanie beží. Keď na bežnom účte zadáš heslo iného účtu správcu, nezmaže nič a svoj priečinok %APPDATA%\MojeKocky zmažeš sám. Záloha je kópia tohto priečinka.`,
      ],
    },
  ]

  const EN_DESKTOP: Section[] = [
    {
      title: 'Where your data is',
      body: [
        String.raw`Everything stays on this computer in %APPDATA%\MojeKocky: the database and its backups, photos, encrypted keys, a remembered sign-in (if you choose it) and the log. The app has no server or operator and its author has no access to the data.`,
        'This is personal, household use, which GDPR does not cover (Art. 2(2)(c)). If several people use the app on this computer, each has their own account with a password.',
      ],
    },
    {
      title: 'What the app stores',
      body: [
        'Account: name, e-mail (if you enter it), password only as a hash (argon2), language and display settings.',
        'Collection: pieces, prices, dates, location, notes, wishlist, categories, saved views, price checks and manual prices.',
        'Photos of pieces, shrunk and without camera data including the GPS location.',
        'Keys to services encrypted with secret.key and a log of service calls for the last 30 days.',
        String.raw`If you tick Remember me when signing in, the sign-in token in the file %APPDATA%\MojeKocky\session.bin, encrypted with secret.key. It lasts 30 days since last use and signing out or deleting the account removes it. Changing the password replaces it with a new one and ends the account’s other sign-ins. Without the tick the sign-in stays only in memory while the window is open, at most 12 hours without use.`,
        String.raw`Before every update of the app to another version, a copy of the whole database in %APPDATA%\MojeKocky\backups. The last 5 backups are kept, older ones are deleted, and the app deletes a backup older than 90 days the next time it starts. Data of a deleted account may remain in them until the backups rotate out, at the longest until the first start of the app after 90 days.`,
      ],
    },
    {
      title: 'What leaves the computer',
      body: [
        'Only questions to services you connect yourself (Rebrickable, Brickset, BrickEconomy, UPCitemdb): set numbers and barcodes under your own key. No personal data.',
        'The Eurostat inflation index when you switch on today’s-money figures. Eurostat receives nothing about you.',
        'Exchange rates from the European Central Bank (ECB) when you pick a display currency other than the euro or enter an amount in a foreign currency. Only the public rates are downloaded, nothing about you is sent.',
        'Set pictures are loaded directly from Rebrickable and Brickset, which see this computer’s IP address.',
      ],
    },
    {
      title: 'Your control',
      body: [
        'In Settings → Account you download all your data (ZIP) or delete the account with everything that belongs to it. It stays in the pre-update backups until they rotate out, at the longest until the first start of the app after 90 days.',
        String.raw`Uninstalling asks whether to delete the data folder of the Windows account it runs as. If you enter a different administrator's password on a standard account, it deletes nothing and you delete your own %APPDATA%\MojeKocky folder yourself. A backup is a copy of that folder.`,
      ],
    },
  ]

  const sections = computed(() => {
    const sk = locale.value === 'sk'
    if (isDesktop) return sk ? SK_DESKTOP : EN_DESKTOP
    return sk ? SK : EN
  })

  const storage = computed(() => [
    // Desktop: okno cookie nemá, prihlasovacie drží most (bridge.py) a zapamätané
    // uloží zašifrované do session.bin v priečinku údajov.
    ...(isDesktop
      ? [{ name: 'session.bin', kind: t('privacy.storage.file'), purpose: t('privacy.storage.rememberedLogin'), lasts: t('privacy.storage.rememberedLoginLasts') }]
      : [{ name: 'lego_refresh', kind: 'cookie', purpose: t('privacy.storage.refresh'), lasts: t('privacy.storage.refreshLasts') }]),
    { name: 'lego-theme', kind: 'localStorage', purpose: t('privacy.storage.theme'), lasts: t('privacy.storage.untilCleared') },
    { name: 'lego-hide-prices', kind: 'localStorage', purpose: t('privacy.storage.hidePrices'), lasts: t('privacy.storage.untilCleared') },
    { name: 'moje-kocky.camera', kind: 'localStorage', purpose: t('privacy.storage.camera'), lasts: t('privacy.storage.untilCleared') },
    { name: 'moje-kocky.portfolio-range', kind: 'localStorage', purpose: t('privacy.storage.range'), lasts: t('privacy.storage.untilCleared') },
    { name: 'moje-kocky.cookie-note', kind: 'localStorage', purpose: t('privacy.storage.note'), lasts: t('privacy.storage.untilCleared') },
  ])
</script>

<template>
  <v-app>
    <v-main class="bg-background">
      <v-container class="privacy" style="max-width: 820px">
        <v-btn class="mb-2" prepend-icon="mdi-arrow-left" to="/prihlasenie" variant="text">
          {{ t('common.back') }}
        </v-btn>

        <h1 class="text-headline-large mb-1">{{ t('privacy.title') }}</h1>
        <div class="text-body-small text-medium-emphasis mb-4">{{ t('privacy.version', { version }) }}</div>

        <v-alert v-if="isDesktop" class="mb-4" type="info" variant="tonal">{{ t('privacy.desktop') }}</v-alert>

        <v-card v-else border class="pa-4 mb-4" flat>
          <div class="text-body-large font-weight-medium mb-1">{{ t('privacy.operator') }}</div>

          <div v-if="operatorName || operatorEmail" class="text-body-large">
            {{ operatorName }}<span v-if="operatorName && operatorEmail">, </span>
            <a v-if="operatorEmail" :href="`mailto:${operatorEmail}`">{{ operatorEmail }}</a>
          </div>

          <v-alert v-else density="compact" type="warning" variant="tonal">{{ t('privacy.noOperator') }}</v-alert>
        </v-card>

        <section v-for="section in sections" :key="section.title" class="mb-5">
          <h2 class="text-title-large font-weight-medium mb-2">{{ section.title }}</h2>

          <ul class="ps-5">
            <li v-for="line in section.body" :key="line" class="text-body-large mb-1">{{ line }}</li>
          </ul>
        </section>

        <section class="mb-5">
          <h2 class="text-title-large font-weight-medium mb-2">{{ isDesktop ? t('privacy.cookiesTitleDesktop') : t('privacy.cookiesTitle') }}</h2>
          <p class="text-body-large mb-3">{{ isDesktop ? t('privacy.cookiesIntroDesktop') : t('privacy.cookiesIntro') }}</p>

          <v-table density="compact">
            <thead>
              <tr>
                <th>{{ t('privacy.storage.name') }}</th>
                <th>{{ t('privacy.storage.kind') }}</th>
                <th>{{ t('privacy.storage.purpose') }}</th>
                <th>{{ t('privacy.storage.lasts') }}</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="row in storage" :key="row.name">
                <td><code>{{ row.name }}</code></td>
                <td>{{ row.kind }}</td>
                <td>{{ row.purpose }}</td>
                <td>{{ row.lasts }}</td>
              </tr>
            </tbody>
          </v-table>
        </section>
      </v-container>
    </v-main>
  </v-app>
</template>
