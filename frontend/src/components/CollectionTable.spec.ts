import type { GroupedItem } from '@/api/types'
import type * as VueUse from '@vueuse/core'
import { enableAutoUnmount, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import { VCard } from 'vuetify/components/VCard'
import { VIcon } from 'vuetify/components/VIcon'
import { createSelection } from '@/composables/useSelection'
import i18n from '@/plugins/i18n'
import { useCollectionStore } from '@/stores/collection'
import CollectionTable from './CollectionTable.vue'

/** Šírka tabuľky, ako ju nameria `useElementSize`. */
const width = ref(1400)

vi.mock('@vueuse/core', async original => ({
  ...(await original<typeof VueUse>()),
  useElementSize: () => ({ width, height: ref(600) }),
}))

enableAutoUnmount(afterEach)

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe (): void {}
    unobserve (): void {}
    disconnect (): void {}
  } as unknown as typeof ResizeObserver
})

const ROW = {
  catalog: { catalog_num: '77245-1', name: 'Aston Martin Aramco F1', theme: 'Speed Champions', year: 2025, image_url: null },
  quantity: 1,
  sold_quantity: 0,
  conditions: { new_sealed: 1 },
  locations: ['Povala · krabica 3'],
  purchase_total: '24.99',
  market_total: '31.20',
  unrealized: '6.21',
  unrealized_pct: 24.85,
  price_at: '2026-10-01T12:00:00Z',
  price_missing: 0,
  price_approx: 0,
} as unknown as GroupedItem

function mountTable () {
  const pinia = createPinia()
  setActivePinia(pinia)
  const collection = useCollectionStore(pinia)
  collection.grouping = 'set' as never
  collection.grouped = [ROW]
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  return mount(CollectionTable, {
    props: { selection: createSelection(), sold: false },
    global: {
      plugins: [i18n, pinia, router, createVuetify({ components: { VCard, VIcon } })],
      stubs: { SetImage: true },
    },
  })
}

describe('tabuľka v Zbierke', () => {
  it('široká tabuľka má stĺpce s hlavičkou', () => {
    i18n.global.locale.value = 'sk'
    width.value = 1400
    const wrapper = mountTable()

    expect(wrapper.find('thead').exists()).toBe(true)
    expect(wrapper.find('[data-test="compact-row"]').exists()).toBe(false)
  })

  it('úzka tabuľka ukáže kompaktný riadok: názov, séria, sumy a stav pod sebou', () => {
    i18n.global.locale.value = 'sk'
    width.value = 600
    const wrapper = mountTable()

    expect(wrapper.find('thead').exists()).toBe(false)
    const row = wrapper.find('[data-test="compact-row"]')
    const text = row.text().replace(/\s+/g, ' ')
    expect(text).toContain('77245-1')
    expect(text).toContain('Aston Martin Aramco F1')
    expect(text).toContain('Speed Champions · 2025 · 1 ks')
    expect(text).toContain('Kúpené 24,99 €')
    expect(text).toContain('Hodnota 31,20 €')
    expect(text).toContain('Povala · krabica 3')
    // Malá fotka vľavo v stĺpci pevnej šírky, nech sú fotky pod sebou.
    const layout = row.find('.compact-layout')
    expect(layout.element.firstElementChild?.classList.contains('compact-photo')).toBe(true)
  })
})
