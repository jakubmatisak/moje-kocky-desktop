import type * as Client from '@/api/client'
import { enableAutoUnmount, flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import SeriesValueCard from './SeriesValueCard.vue'

let answer: Record<string, unknown> = {}

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async () => ({ data: answer }),
  },
}))

enableAutoUnmount(afterEach)

function value (overrides: Record<string, unknown> = {}) {
  return {
    owned_count: 4,
    distinct_count: 3,
    duplicates: 1,
    series_size: 3,
    complete: true,
    single: false,
    priced_count: 4,
    purchase_total: '17.00',
    market_total: '25.50',
    profit: '8.50',
    profit_pct: 50,
    approx: false,
    price_at: '2026-09-03T12:00:00Z',
    history: [],
    ...overrides,
  }
}

async function mountCard (capabilities: string[] = []) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore(pinia)
  auth.keys = { capabilities } as never
  const wrapper = shallowMount(SeriesValueCard, {
    props: { num: '42233' },
    global: { plugins: [i18n, pinia], renderStubDefaultSlot: true },
  })
  await flushPromises()
  return wrapper
}

describe('Séria: cena mojich figúrok', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('upozorní, že sa duplikáty pripočítavajú', async () => {
    answer = value()
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-duplicates"]').text()).toContain('1 duplikát')
    expect(wrapper.find('[data-test="series-market"]').text()).toContain('25,50')
  })

  it('hodnota jednej série sa nedá zapnúť pri nekompletnej sérii', async () => {
    answer = value({ complete: false, duplicates: 0, distinct_count: 2, owned_count: 2 })
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-single"]').attributes('disabled')).toBe('true')
    expect(wrapper.find('[data-test="series-duplicates"]').exists()).toBe(false)
  })

  it('bez ceny pomlčka, nie nula', async () => {
    answer = value({ market_total: null, profit: null, profit_pct: null, priced_count: 0, price_at: null })
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-market"]').text()).toBe('—')
  })

  it('obnova cien len s kľúčom BrickEconomy', async () => {
    answer = value()
    expect((await mountCard()).find('[data-test="series-refresh"]').exists()).toBe(false)
    expect((await mountCard(['brickeconomy.price_detail'])).find('[data-test="series-refresh"]').exists()).toBe(true)
  })

  it('bez vlastnej figúrky zo série sa karta neukáže', async () => {
    answer = value({ owned_count: 0, distinct_count: 0, duplicates: 0, market_total: null })
    const wrapper = await mountCard()

    expect(wrapper.html()).toBe('<!--v-if-->')
  })
})
