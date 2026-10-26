import type * as Client from '@/api/client'
import { enableAutoUnmount, flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import SeriesValueCard from './SeriesValueCard.vue'

let answer: Record<string, unknown> = {}
const HISTORY = [
  { captured_at: '2026-09-01T12:00:00Z', avg_price: '9.50' },
  { captured_at: '2026-09-02T12:00:00Z', avg_price: '10.50' },
]
const HISTORY_USED = [
  { captured_at: '2026-09-01T12:00:00Z', avg_price: '5.00', condition: 'U' },
  { captured_at: '2026-09-02T12:00:00Z', avg_price: '5.50', condition: 'U' },
]
const EVENTS = [{ day: '2026-09-01', kind: 'buy', count: 2, amount: '7.00' }]

let loads = 0
const changeListeners: Array<() => void> = []
let plan: Record<string, unknown> = { calls: 2, fresh: 1, max_age_days: 15 }
const posted: unknown[] = []

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async (path: string) => {
      if (path === '/prices/series/{num}/refresh-plan') {
        return { data: plan }
      }
      if (path === '/prices/refresh-status') {
        return { data: { running: false, calls_left: 63, calls_limit: 100, calls_used: 37 } }
      }
      loads += 1
      return { data: answer }
    },
    POST: async (path: string, options: unknown) => {
      posted.push([path, options])
      return { data: { running: false, updated: 2, calls_left: 61 } }
    },
  },
  onCollectionChanged: (listener: () => void) => {
    changeListeners.push(listener)
    return () => changeListeners.splice(changeListeners.indexOf(listener), 1)
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
    history: HISTORY,
    history_used: HISTORY_USED,
    estimated_until: '2026-09-02',
    events: EVENTS,
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

  it('po kúpe, úprave či zmazaní figúrok sa karta aj graf načítajú znova', async () => {
    answer = value()
    await mountCard()
    const before = loads

    for (const listener of changeListeners) {
      listener()
    }
    await flushPromises()

    expect(loads).toBe(before + 1)
  })

  it('graf je súčet histórie cien z BrickEconomy s nákupmi a riadkom o odhade', async () => {
    answer = value()
    const wrapper = await mountCard()

    const chart = wrapper.findComponent({ name: 'PriceHistoryChart' })
    expect(chart.props('newPoints')).toEqual(HISTORY)
    // Druhá čiara Rozbalený, ako v grafe setu.
    expect(chart.props('usedPoints')).toEqual(HISTORY_USED)
    expect(chart.props('events')).toEqual(EVENTS)
    expect(chart.props('purchase')).toBe(17)
    expect(wrapper.find('[data-test="series-estimated"]').text().replace(/\s/g, ' ')).toContain('2. 9. 2026')
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

  it('bez figúrok v katalógu a bez vlastnej figúrky sa karta neukáže', async () => {
    answer = value({ owned_count: 0, distinct_count: 0, duplicates: 0, market_total: null, member_count: 0 })
    const wrapper = await mountCard()

    expect(wrapper.html()).toBe('<!--v-if-->')
  })
})

const WHOLE = [
  { captured_at: '2026-09-01T12:00:00Z', avg_price: '18.50' },
  { captured_at: '2026-09-03T12:00:00Z', avg_price: '19.50' },
]

function nothingOwned (overrides: Record<string, unknown> = {}) {
  return value({
    owned_count: 0, distinct_count: 0, duplicates: 0, complete: false, priced_count: 0,
    purchase_total: '0.00', market_total: null, profit: null, profit_pct: null, price_at: null,
    history: [], history_used: [], estimated_until: null, events: [],
    member_count: 3, missing_count: 3, missing_priced: 3, missing_total: '19.50',
    series_priced: 3, series_total: '19.50', history_all: WHOLE,
    ...overrides,
  })
}

describe('Séria: cena celej série a chýbajúcich figúrok', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
    posted.length = 0
    plan = { calls: 2, fresh: 1, max_age_days: 15 }
  })

  it('séria, z ktorej nemám nič, ukáže cenu celej série a zelenú čiaru', async () => {
    answer = nothingOwned()
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-whole"]').text()).toContain('19,50')
    expect(wrapper.find('[data-test="series-market"]').exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'PriceHistoryChart' }).props('wholePoints')).toEqual(WHOLE)
  })

  it('pri sérii, z ktorej niečo mám, sú chýbajúce figúrky zelenou', async () => {
    answer = value({ member_count: 3, missing_count: 1, missing_priced: 1, missing_total: '9.00', series_priced: 3, series_total: '19.50', history_all: WHOLE })
    const wrapper = await mountCard()

    const missing = wrapper.find('[data-test="series-missing"]')
    expect(missing.text()).toContain('9,00')
    expect(missing.find('.text-positive').exists()).toBe(true)
    expect(wrapper.find('[data-test="series-whole"]').text()).toContain('19,50')
  })

  it('povie, koľko figúrok ešte nemá cenu', async () => {
    answer = nothingOwned({ series_priced: 2, series_total: '10.50', missing_priced: 2, missing_total: '10.50', history_all: [] })
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-unpriced"]').text()).toContain('bez ceny: 1 figúrka')
  })

  it('Zistiť ceny chýbajúcich najprv povie, koľko volaní to stojí, a stiahne až po potvrdení', async () => {
    answer = nothingOwned()
    const wrapper = await mountCard(['brickeconomy.price_detail'])

    await wrapper.find('[data-test="series-whole-refresh"]').trigger('click')
    await flushPromises()
    expect(posted).toEqual([])
    const text = wrapper.find('[data-test="series-whole-confirm-text"]').text()
    expect(text).toContain('2 figúrok')
    expect(text).toContain('15 dní')
    expect(text).toContain('63 zo 100')

    await wrapper.find('[data-test="series-whole-confirm"]').trigger('click')
    await flushPromises()
    expect(posted).toEqual([['/prices/refresh-all', { params: { query: { num: '42233', whole_series: true } } }]])
  })

  it('keď sú všetky ceny aktuálne, nevolá nič a povie to', async () => {
    plan = { calls: 0, fresh: 3, max_age_days: 15 }
    answer = nothingOwned()
    const wrapper = await mountCard(['brickeconomy.price_detail'])

    await wrapper.find('[data-test="series-whole-refresh"]').trigger('click')
    await flushPromises()

    expect(posted).toEqual([])
    expect(wrapper.find('[data-test="series-whole-fresh"]').text()).toContain('15 dní')
  })

  it('tlačidlo len s kľúčom BrickEconomy a keď niečo chýba', async () => {
    answer = nothingOwned()
    expect((await mountCard()).find('[data-test="series-whole-refresh"]').exists()).toBe(false)
    answer = value({ member_count: 3, missing_count: 0, series_total: '19.50', series_priced: 3 })
    expect((await mountCard(['brickeconomy.price_detail'])).find('[data-test="series-whole-refresh"]').exists()).toBe(false)
  })
})

describe('Séria: po stiahnutí cien celej série', () => {
  it('oznámi stránke, nech načíta aj ceny pri chýbajúcich figúrkach', async () => {
    i18n.global.locale.value = 'sk'
    plan = { calls: 2, fresh: 0, max_age_days: 15 }
    answer = nothingOwned()
    const wrapper = await mountCard(['brickeconomy.price_detail'])

    await wrapper.find('[data-test="series-whole-refresh"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-test="series-whole-confirm"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('prices-updated')).toHaveLength(1)
  })
})

describe('Séria: počet figúrok pri sumách', () => {
  it('Chýba mi aj Celá séria majú štítok s počtom figúrok', async () => {
    i18n.global.locale.value = 'sk'
    answer = value({ member_count: 12, missing_count: 5, missing_priced: 5, missing_total: '107.62', series_priced: 12, series_total: '243.28', history_all: WHOLE })
    const wrapper = await mountCard()

    expect(wrapper.find('[data-test="series-missing-count"]').text()).toBe('5 figúrok')
    expect(wrapper.find('[data-test="series-whole-count"]').text()).toBe('12 figúrok')
  })
})
