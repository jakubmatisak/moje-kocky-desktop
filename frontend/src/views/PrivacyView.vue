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
        'Záznam volaní cudzích služieb (čo, kedy, s akým výsledkom) a prihlasovacie tokeny, oboje 30 dní.',
      ],
    },
    {
      title: 'Prečo a na akom základe',
      body: [
        'Aby appka mohla viesť tvoju evidenciu: plnenie zmluvy, čl. 6 ods. 1 písm. b GDPR.',
        'Záznam volaní a tokeny kvôli bezpečnosti a stráženiu denných limitov služieb: oprávnený záujem, čl. 6 ods. 1 písm. f GDPR.',
        'Appka nepoužíva reklamu, analytiku ani sledovanie a údaje nepredáva.',
      ],
    },
    {
      title: 'Ako dlho',
      body: [
        'Údaje účtu a zbierky, kým účet nezmažeš. Záznam volaní a tokeny 30 dní.',
        'Pred každou aktualizáciou appky na inú verziu sa celá databáza zálohuje na server do priečinka backups. Uchováva sa 5 posledných záloh, staršie sa mažú. Údaje zmazaného účtu v nich môžu ostať, kým sa zálohy neprestriedajú.',
      ],
    },
    {
      title: 'Kto ich dostane',
      body: [
        isDesktop
          ? String.raw`Nikto: desktopová appka má všetky údaje len na tomto počítači, v priečinku %APPDATA%\MojeKocky.`
          : 'Poskytovateľ hostingu, na ktorom appka beží.',
        'Služby, ktoré si pripojíš vlastným kľúčom, dostanú len čísla setov a čiarové kódy, na ktoré sa pýtaš, nie tvoje osobné údaje. Eurostat nedostane nič, čo by sa ťa týkalo.',
        isDesktop
          ? 'Fotky setov sa načítavajú priamo z Rebrickable a Brickset, tie vidia IP adresu tohto počítača.'
          : 'Fotky setov sa načítavajú cez server appky, takže Rebrickable ani Brickset nevidia tvoju IP adresu.',
      ],
    },
    {
      title: 'Tvoje práva',
      body: [
        'Prístup a prenosnosť: v Nastaveniach → Účet si stiahneš všetky svoje údaje aj fotky (ZIP).',
        'Oprava: údaje zmeníš priamo v appke.',
        'Vymazanie: v Nastaveniach → Účet zmažeš účet so všetkým, čo k nemu patrí. V zálohách pred aktualizáciou ostane, kým sa neprestriedajú (pozri Ako dlho).',
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
        'A log of calls to external services (what, when, with what result) and sign-in tokens, both for 30 days.',
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
        'Account and collection data until you delete the account. Call log and tokens 30 days.',
        'Before every update of the app to another version, the whole database is backed up on the server to the backups folder. The last 5 backups are kept, older ones are deleted. Data of a deleted account may remain in them until the backups rotate out.',
      ],
    },
    {
      title: 'Who receives it',
      body: [
        isDesktop
          ? String.raw`Nobody: the desktop app keeps all data on this computer only, in %APPDATA%\MojeKocky.`
          : 'The hosting provider the app runs on.',
        'Services you connect with your own key receive only the set numbers and barcodes you ask about, not your personal data. Eurostat receives nothing about you.',
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
        'Erasure: in Settings → Account you delete the account with everything that belongs to it. It stays in the pre-update backups until they rotate out (see How long).',
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
        String.raw`Všetko je len na tomto počítači v priečinku %APPDATA%\MojeKocky: databáza, fotky, zašifrované kľúče a denník. Appka nemá server ani prevádzkovateľa a autor k údajom nemá prístup.`,
        'Ide o osobné použitie v domácnosti; na také spracúvanie sa GDPR nevzťahuje (čl. 2 ods. 2 písm. c). Ak na počítači používa appku viac ľudí, každý má svoj účet s heslom.',
      ],
    },
    {
      title: 'Čo appka ukladá',
      body: [
        'Účet: meno, e-mail (ak ho zadáš), heslo len ako odtlačok (argon2), jazyk a nastavenia zobrazenia.',
        'Zbierku: kusy, ceny, dátumy, umiestnenie, poznámky, Chcem, kategórie, uložené pohľady, overené a ručne zadané ceny.',
        'Fotky kusov, zmenšené a bez údajov fotoaparátu vrátane polohy GPS.',
        'Kľúče k službám zašifrované súborom secret.key a záznam volaní služieb za posledných 30 dní.',
      ],
    },
    {
      title: 'Čo odchádza z počítača',
      body: [
        'Len otázky na služby, ktoré si sám pripojíš (Rebrickable, Brickset, BrickEconomy, UPCitemdb): čísla setov a čiarové kódy pod tvojím vlastným kľúčom. Osobné údaje nie.',
        'Index inflácie z Eurostatu, keď prepočet do dnešných peňazí zapneš. Eurostat nedostane nič o tebe.',
        'Obrázky setov sa načítavajú priamo z Rebrickable a Brickset, tie vidia IP adresu tohto počítača.',
      ],
    },
    {
      title: 'Tvoja kontrola',
      body: [
        'V Nastaveniach → Účet si stiahneš všetky svoje údaje (ZIP) alebo zmažeš účet so všetkým, čo k nemu patrí.',
        String.raw`Pri odinštalovaní sa appka opýta, či zmazať aj priečinok s údajmi. Záloha je kópia priečinka %APPDATA%\MojeKocky.`,
      ],
    },
  ]

  const EN_DESKTOP: Section[] = [
    {
      title: 'Where your data is',
      body: [
        String.raw`Everything stays on this computer in %APPDATA%\MojeKocky: the database, photos, encrypted keys and the log. The app has no server or operator and its author has no access to the data.`,
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
      ],
    },
    {
      title: 'What leaves the computer',
      body: [
        'Only questions to services you connect yourself (Rebrickable, Brickset, BrickEconomy, UPCitemdb): set numbers and barcodes under your own key. No personal data.',
        'The Eurostat inflation index when you switch on today’s-money figures. Eurostat receives nothing about you.',
        'Set pictures are loaded directly from Rebrickable and Brickset, which see this computer’s IP address.',
      ],
    },
    {
      title: 'Your control',
      body: [
        'In Settings → Account you download all your data (ZIP) or delete the account with everything that belongs to it.',
        String.raw`Uninstalling asks whether to delete the data folder too. A backup is a copy of %APPDATA%\MojeKocky.`,
      ],
    },
  ]

  const sections = computed(() => {
    const sk = locale.value === 'sk'
    if (isDesktop) return sk ? SK_DESKTOP : EN_DESKTOP
    return sk ? SK : EN
  })

  const storage = computed(() => [
    // Desktop: prihlásenie drží appka v pamäti, v okne nie je žiadne cookie.
    ...(isDesktop ? [] : [{ name: 'lego_refresh', kind: 'cookie', purpose: t('privacy.storage.refresh'), lasts: t('privacy.storage.days30') }]),
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

        <h1 class="text-h4 mb-1">{{ t('privacy.title') }}</h1>
        <div class="text-caption text-medium-emphasis mb-4">{{ t('privacy.version', { version }) }}</div>

        <v-alert v-if="isDesktop" class="mb-4" type="info" variant="tonal">{{ t('privacy.desktop') }}</v-alert>

        <v-card v-else border class="pa-4 mb-4" flat>
          <div class="text-subtitle-1 font-weight-medium mb-1">{{ t('privacy.operator') }}</div>

          <div v-if="operatorName || operatorEmail" class="text-body-1">
            {{ operatorName }}<span v-if="operatorName && operatorEmail">, </span>
            <a v-if="operatorEmail" :href="`mailto:${operatorEmail}`">{{ operatorEmail }}</a>
          </div>

          <v-alert v-else density="compact" type="warning" variant="tonal">{{ t('privacy.noOperator') }}</v-alert>
        </v-card>

        <section v-for="section in sections" :key="section.title" class="mb-5">
          <h2 class="text-h6 mb-2">{{ section.title }}</h2>

          <ul class="ps-5">
            <li v-for="line in section.body" :key="line" class="text-body-1 mb-1">{{ line }}</li>
          </ul>
        </section>

        <section class="mb-5">
          <h2 class="text-h6 mb-2">{{ isDesktop ? t('privacy.cookiesTitleDesktop') : t('privacy.cookiesTitle') }}</h2>
          <p class="text-body-1 mb-3">{{ isDesktop ? t('privacy.cookiesIntroDesktop') : t('privacy.cookiesIntro') }}</p>

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
