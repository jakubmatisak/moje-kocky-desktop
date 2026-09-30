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

async function text (): Promise<string> {
  const wrapper = shallowMount(PrivacyView, {
    global: { plugins: [i18n], config: { warnHandler: () => {} } },
  })
  await flushPromises()
  return wrapper.text()
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
    expect(body).not.toContain('on the server')
  })
})
