import type * as Client from '@/api/client'
import type * as Router from 'vue-router'
import type * as Vuetify from 'vuetify'
import { flushPromises, RouterLinkStub, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FiguresElsewhere from '@/components/FiguresElsewhere.vue'
import i18n from '@/plugins/i18n'
import { useFilterStore } from '@/stores/filters'
import CollectionView from './CollectionView.vue'

let query: Record<string, string> = {}
let facets: Record<string, unknown> = {}
let grouped: unknown[] = []

vi.mock('vue-router', async original => ({
  ...(await original<typeof Router>()),
  useRoute: () => ({ params: {}, query }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(async () => {}), back: vi.fn() }),
}))

// Široká obrazovka s panelom filtrov, ako na počítači.
vi.mock('vuetify', async original => ({
  ...(await original<typeof Vuetify>()),
  useDisplay: () => ({ mdAndUp: { value: true } }),
}))

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async (path: string) => {
      if (path === '/items/facets') {
        return { data: facets }
      }
      if (path === '/items/grouped') {
        return { data: grouped }
      }
      if (path === '/auth/me/preferences' || path === '/suggestions') {
        return { data: {} }
      }
      if (path === '/stats/summary') {
        return { data: null }
      }
      return { data: [] }
    },
    POST: async () => ({ data: {} }),
    PUT: async () => ({ data: {} }),
  },
}))

const TITANIC = { catalog: { catalog_num: '10294-1', name: 'Titanic' }, items: [] }

function facetsWith (hidden: number, total: number): Record<string, unknown> {
  return { total, hidden_figures: hidden, totals: null }
}

async function mountCollection () {
  // Riadok o figúrkach sa vykreslí naozaj, ostatné časti stránky ostanú stubmi.
  const wrapper = shallowMount(CollectionView, {
    global: {
      plugins: [i18n],
      stubs: { FiguresElsewhere: false, RouterLink: RouterLinkStub },
      config: { warnHandler: () => {} },
    },
  })
  await flushPromises()
  return wrapper
}

describe('Zbierka: riadok o figúrkach zo sérií len vtedy, keď na tom záleží', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'sk'
  })

  it('bežný filter bez hľadania, ktorý niečo ukazuje, figúrky nehlási', async () => {
    query = { condition: 'new_sealed' }
    grouped = [TITANIC]
    facets = facetsWith(77, 1)
    const wrapper = await mountCollection()

    expect(wrapper.find('v-empty-state').exists()).toBe(false)
    expect(wrapper.findComponent(FiguresElsewhere).exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Figúrkach')
  })

  it('hľadanie, ktoré trafí figúrky, dá jeden riadok pod súčty nad výsledok', async () => {
    query = { q: 'shrek' }
    grouped = [TITANIC]
    facets = facetsWith(3, 1)
    const wrapper = await mountCollection()

    const lines = wrapper.findAllComponents(FiguresElsewhere)
    expect(lines).toHaveLength(1)
    expect(lines[0]!.find('v-alert').exists()).toBe(false)
    expect(lines[0]!.text()).toContain('3 figúrky zo sérií sú vo Figúrkach')

    // Pod riadkom súčtov, nad kartami.
    const html = wrapper.html()
    const line = html.indexOf('vo Figúrkach')
    expect(html.indexOf('<selection-totals-stub')).toBeLessThan(line)
    expect(line).toBeLessThan(html.indexOf('class="collection-results'))
  })

  it('prázdny výsledok povie o figúrkach v prázdnom stave, nie nad ním', async () => {
    query = { condition: 'new_sealed' }
    grouped = []
    facets = facetsWith(1, 0)
    const wrapper = await mountCollection()

    const empty = wrapper.find('v-empty-state')
    expect(empty.attributes('title')).toBe('Nič sa nenašlo')
    expect(empty.text()).toContain('1 figúrka zo série je vo Figúrkach')
    expect(wrapper.findAllComponents(FiguresElsewhere)).toHaveLength(1)
  })

  it('prázdne hľadanie ukáže riadok len v prázdnom stave, nie dvakrát', async () => {
    query = { q: 'donkey' }
    grouped = []
    facets = facetsWith(12, 0)
    const wrapper = await mountCollection()

    expect(wrapper.findAllComponents(FiguresElsewhere)).toHaveLength(1)
    expect(wrapper.find('v-empty-state').text()).toContain('12 figúrok zo sérií je vo Figúrkach')
  })

  it('prázdny výsledok bez figúrok ostane obyčajné „Nič sa nenašlo“', async () => {
    query = { q: 'titanik' }
    grouped = []
    facets = facetsWith(0, 0)
    const wrapper = await mountCollection()

    expect(wrapper.find('v-empty-state').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Figúrkach')
  })

  it('počet čaká na hľadanie: kým počty patria starému filtru, riadok nie je', async () => {
    // Len oneskorené načítanie po písaní; flushPromises ide cez setImmediate.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      query = { condition: 'new_sealed' }
      grouped = [TITANIC]
      facets = facetsWith(77, 1)
      const wrapper = await mountCollection()

      // Písanie do hľadania: počty prídu až po chvíli, dovtedy je 77 z filtra stavu.
      facets = facetsWith(2, 1)
      useFilterStore().filters.q = 'shrek'
      await flushPromises()
      expect(wrapper.findComponent(FiguresElsewhere).exists()).toBe(false)

      await vi.advanceTimersByTimeAsync(300)
      await flushPromises()
      expect(wrapper.findComponent(FiguresElsewhere).text()).toContain('2 figúrky zo sérií sú vo Figúrkach')
    } finally {
      vi.useRealTimers()
    }
  })

  it('po anglicky', async () => {
    i18n.global.locale.value = 'en'
    query = { q: 'shrek' }
    grouped = [TITANIC]
    facets = facetsWith(4, 1)
    const wrapper = await mountCollection()

    const line = wrapper.findComponent(FiguresElsewhere)
    expect(line.text()).toContain('4 series minifigures are in Minifigures')
    expect(line.findComponent(RouterLinkStub).text()).toBe('Open Minifigures')
  })
})
