import type * as Client from '@/api/client'
import type * as Bridge from '@/desktop/bridge'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import AppVersion from '@/components/AppVersion.vue'
import i18n from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import SettingsView from './SettingsView.vue'

// Desktop nemá prevádzkovateľa ani odkazy na zdieľanie, verziu appky áno.
vi.mock('@/desktop/bridge', async original => ({
  ...(await original<typeof Bridge>()),
  isDesktop: true,
}))

/** Odpoveď `/admin/settings`; ostatné volania nevracajú nič. */
const server = vi.hoisted(() => ({
  appSettings: null as { allow_registration: boolean, env_default: boolean } | null,
}))

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async (path: string) => ({ data: path === '/admin/settings' ? server.appSettings : null }),
  },
}))

async function mountAsAdmin () {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth.user = { id: 1, email: 'ja@doma.sk', display_name: 'Ja', role: 'admin', locale: 'sk' } as typeof auth.user
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/nastavenia', name: 'settings', component: SettingsView }],
  })
  await router.push('/nastavenia?tab=app')
  const wrapper = shallowMount(SettingsView, {
    global: { plugins: [i18n, router, createVuetify()], config: { warnHandler: () => {} } },
  })
  await flushPromises()
  return wrapper
}

describe('Nastavenia v desktope', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
    server.appSettings = null
  })

  it('karta Aplikácia ukáže verziu appky, prevádzkovateľa nie', async () => {
    const wrapper = await mountAsAdmin()

    expect(wrapper.findComponent(AppVersion).exists()).toBe(true)
    expect(wrapper.text()).not.toContain(i18n.global.t('settings.operatorTitle'))
    expect(wrapper.text()).not.toContain(i18n.global.t('settings.tabs.sharing'))
  })

  it('otvorená registrácia hovorí o tomto počítači, nie o adrese appky a .env', async () => {
    server.appSettings = { allow_registration: true, env_default: false }

    const wrapper = await mountAsAdmin()
    const text = wrapper.text()

    expect(text).toContain(i18n.global.t('settings.registrationOpenHintDesktop'))
    expect(text).toContain(i18n.global.t('settings.registrationFirstHintDesktop'))
    expect(text).not.toContain(i18n.global.t('settings.registrationOpenHint'))
    expect(text).not.toContain('.env')
  })
})
