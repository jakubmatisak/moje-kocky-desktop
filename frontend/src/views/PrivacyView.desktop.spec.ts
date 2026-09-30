import type * as Client from '@/api/client'
import type * as Bridge from '@/desktop/bridge'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/plugins/i18n'
import PrivacyView from './PrivacyView.vue'

// Desktop: zásady majú vlastné sekcie (údaje sú v %APPDATA%\MojeKocky, žiadny server).
vi.mock('@/desktop/bridge', async original => ({
  ...(await original<typeof Bridge>()),
  isDesktop: true,
}))

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async () => ({ data: { registration_open: false, operator_name: null, operator_email: null, privacy_version: 'x' } }),
  },
}))

async function mountView () {
  const wrapper = shallowMount(PrivacyView, {
    global: { plugins: [i18n], config: { warnHandler: () => {} } },
  })
  await flushPromises()
  return wrapper
}

async function text (): Promise<string> {
  return (await mountView()).text()
}

/** Riadky tabuľky úložiska: názov, druh, na čo, ako dlho. */
async function storageRows (): Promise<string[][]> {
  const wrapper = await mountView()
  return wrapper.findAll('tbody tr').map(row => row.findAll('td').map(cell => cell.text()))
}

describe('zásady desktopu: zálohy pred aktualizáciou', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('slovenský text povie, že zálohy sú v priečinku údajov na tomto počítači a ako dlho ostanú', async () => {
    i18n.global.locale.value = 'sk'
    const body = await text()

    expect(body).toContain('Kde sú tvoje údaje')
    expect(body).toContain(String.raw`%APPDATA%\MojeKocky\backups`)
    expect(body).toContain('Pred každou aktualizáciou appky na inú verziu')
    expect(body).toContain('5 posledných záloh')
    expect(body).toContain('zmazaného účtu')
    // Zálohy nemajú ostať natrvalo, ani keď nová verzia dlho nevyjde.
    expect(body).toContain('staršiu než 90 dní')
    expect(body).toContain('najdlhšie do prvého štartu appky po 90 dňoch')
    // Tvoja kontrola: zmazaný účet v zálohách tiež najviac 90 dní.
    expect(body).toContain('kým sa neprestriedajú, najdlhšie do prvého štartu appky po 90 dňoch.')
    // Desktop nemá server, zálohy sú na tomto počítači.
    expect(body).not.toContain('na server')
  })

  it('anglický text povie to isté', async () => {
    i18n.global.locale.value = 'en'
    const body = await text()

    expect(body).toContain('Where your data is')
    expect(body).toContain(String.raw`%APPDATA%\MojeKocky\backups`)
    expect(body).toContain('Before every update of the app to another version')
    expect(body).toContain('last 5 backups')
    expect(body).toContain('deleted account')
    expect(body).toContain('older than 90 days')
    expect(body).toContain('until the first start of the app after 90 days')
    expect(body).toContain('until they rotate out, at the longest until the first start of the app after 90 days.')
    expect(body).not.toContain('on the server')
  })
})

describe('zásady desktopu: odinštalovanie', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('slovenský text povie, čí priečinok sa pri odinštalovaní zmaže a čo pri hesle iného správcu', async () => {
    i18n.global.locale.value = 'sk'
    const body = await text()

    expect(body).toContain('priečinok s údajmi účtu Windows, pod ktorým odinštalovanie beží')
    expect(body).toContain('heslo iného účtu správcu, nezmaže nič')
  })

  it('anglický text povie to isté', async () => {
    i18n.global.locale.value = 'en'
    const body = await text()

    expect(body).toContain('data folder of the Windows account it runs as')
    expect(body).toContain('different administrator\'s password on a standard account, it deletes nothing')
  })
})

describe('zásady desktopu: zapamätané prihlásenie', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('slovenský text povie, kde je súbor so zapamätaným prihlásením a čo ho zmaže', async () => {
    i18n.global.locale.value = 'sk'
    const body = await text()

    expect(body).toContain(String.raw`%APPDATA%\MojeKocky\session.bin`)
    expect(body).toContain('Zapamätať si prihlásenie')
    expect(body).toContain('zašifrovaný súborom secret.key')
    expect(body).toContain('zmaže ho odhlásenie aj zmazanie účtu')
    // Zmena hesla v tomto okne zapamätanie nechá, len s novým tokenom.
    expect(body).toContain('Zmena hesla ho vymení za nový a ostatné prihlásenia účtu zruší.')
    expect(body).toContain('kým je okno otvorené, najviac 12 hodín bez použitia')
    expect(body).toContain('zašifrované kľúče, zapamätané prihlásenie (ak si ho zvolíš) a denník')
    // Okno cookie nemá; tabuľka úložiska okna ho nesmie uvádzať.
    expect(body).not.toContain('lego_refresh')
  })

  it('anglický text povie to isté', async () => {
    i18n.global.locale.value = 'en'
    const body = await text()

    expect(body).toContain(String.raw`%APPDATA%\MojeKocky\session.bin`)
    expect(body).toContain('Remember me')
    expect(body).toContain('encrypted with secret.key')
    expect(body).toContain('signing out or deleting the account removes it')
    expect(body).toContain('Changing the password replaces it with a new one and ends the account’s other sign-ins.')
    expect(body).toContain('while the window is open, at most 12 hours without use')
    expect(body).toContain('encrypted keys, a remembered sign-in (if you choose it) and the log')
  })
})

describe('zásady desktopu: cookies a úložisko', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('slovenský text netvrdí, že appka cookies nepoužíva, a povie, kde je zapamätané prihlásenie', async () => {
    i18n.global.locale.value = 'sk'
    const body = await text()

    // Prihlasovacie cookie drží most a zapamätané ukladá do session.bin.
    expect(body).not.toContain('Appka nepoužíva cookies')
    expect(body).toContain('Okno nepoužíva cookies na sledovanie')
    expect(body).toContain(String.raw`zašifrované v súbore %APPDATA%\MojeKocky\session.bin; platí 30 dní od posledného použitia a odhlásenie ho zmaže`)
  })

  it('anglický text povie to isté', async () => {
    i18n.global.locale.value = 'en'
    const body = await text()

    expect(body).not.toContain('The app uses no cookies')
    expect(body).toContain('The window uses no cookies for tracking')
    expect(body).toContain(String.raw`encrypted in the file %APPDATA%\MojeKocky\session.bin; it lasts 30 days since last use and signing out deletes it`)
  })

  it('tabuľka úložiska má riadok session.bin', async () => {
    i18n.global.locale.value = 'sk'
    const rows = await storageRows()

    expect(rows.find(row => row[0] === 'session.bin')).toEqual([
      'session.bin',
      'súbor',
      'Zapamätané prihlásenie (len keď zaškrtneš Zapamätať si prihlásenie), zašifrované',
      '30 dní od posledného použitia; zmaže ho odhlásenie',
    ])
    expect(rows.map(row => row[0])).not.toContain('lego_refresh')
  })

  it('anglická tabuľka tiež', async () => {
    i18n.global.locale.value = 'en'
    const rows = await storageRows()

    expect(rows.find(row => row[0] === 'session.bin')).toEqual([
      'session.bin',
      'file',
      'Remembered sign-in (only if you tick Remember me), encrypted',
      '30 days since last use; signing out deletes it',
    ])
  })
})
