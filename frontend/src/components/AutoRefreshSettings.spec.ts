import type * as Client from '@/api/client'
import { enableAutoUnmount, flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import AutoRefreshSettings from './AutoRefreshSettings.vue'

const puts: Array<{ key: string, body: unknown }> = []
let stored: Record<string, unknown> = {}

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async (path: string) => {
      if (path === '/auth/me/preferences') {
        return { data: stored }
      }
      if (path === '/prices/refresh-status') {
        return { data: { running: false, auto_last: { at: '2026-10-04T07:02', updated: 23, outcome: 'ok', complete: true } } }
      }
      return { data: {} }
    },
    PUT: async (_path: string, options: { params: { path: { key: string } }, body: unknown }) => {
      puts.push({ key: options.params.path.key, body: options.body })
      return { data: {} }
    },
  },
}))

enableAutoUnmount(afterEach)

async function mountSettings (capabilities: string[]) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore(pinia)
  auth.user = { id: 1 } as never
  auth.keys = { capabilities } as never
  const wrapper = shallowMount(AutoRefreshSettings, {
    global: { plugins: [i18n, pinia], renderStubDefaultSlot: true },
  })
  await flushPromises()
  return wrapper
}

describe('Nastavenia: automatická obnova cien', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
    puts.length = 0
    stored = {}
  })

  it('bez kľúča BrickEconomy je prepínač zakázaný a čas ani počet nie sú', async () => {
    const wrapper = await mountSettings([])

    expect(wrapper.find('[data-test="auto-refresh-switch"]').attributes('disabled')).toBe('true')
    expect(wrapper.find('[data-test="auto-refresh-time"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('treba kľúč BrickEconomy')
  })

  it('predvolene 7:00 a 80 cien; zapnutie to uloží pri účte', async () => {
    const wrapper = await mountSettings(['brickeconomy.prices'])

    expect(wrapper.find('[data-test="auto-refresh-time"]').attributes('modelvalue')).toBe('07:00')
    expect(wrapper.find('[data-test="auto-refresh-limit"]').attributes('modelvalue')).toBe('80')

    // Prepínač (v-switch) nastaví model a zavolá uloženie.
    const vm = wrapper.vm as unknown as { enabled: boolean, save: () => Promise<void> }
    vm.enabled = true
    await vm.save()
    await flushPromises()

    expect(puts.at(-1)).toEqual({ key: 'autoRefresh', body: { enabled: true, time: '07:00', limit: 80 } })
  })

  it('uložený čas a počet sa načítajú a ukáže sa posledný beh', async () => {
    stored = { autoRefresh: { enabled: true, time: '21:15', limit: 40 } }
    const wrapper = await mountSettings(['brickeconomy.prices'])

    expect(wrapper.find('[data-test="auto-refresh-time"]').attributes('modelvalue')).toBe('21:15')
    expect(wrapper.find('[data-test="auto-refresh-limit"]').attributes('modelvalue')).toBe('40')
    expect(wrapper.find('[data-test="auto-refresh-last"]').text()).toContain('obnovené ceny: 23')
  })
})
