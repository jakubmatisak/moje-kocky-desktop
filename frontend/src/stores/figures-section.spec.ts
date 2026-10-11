import type * as Client from '@/api/client'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCollectionStore } from './collection'
import { useFilterStore } from './filters'

const get = vi.fn()

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: { GET: (...args: unknown[]) => get(...args) },
}))

describe('Moje figúrky: tá istá Zbierka, len s figúrkami zo sérií', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    get.mockReset()
    get.mockResolvedValue({ data: null })
  })

  it('zoznam, počty aj hromadná úprava sa pýtajú len na figúrky', async () => {
    const store = useFilterStore()
    store.setSection('figures')
    store.filters.box = ['Povala · krabica 3']

    expect(useCollectionStore().filterQuery()).toMatchObject({
      status: 'owned',
      box: ['Povala · krabica 3'],
      figures_only: true,
    })
    expect(useCollectionStore().filterQuery()).not.toHaveProperty('sets_only')

    await store.loadFacets('owned')
    const [, init] = get.mock.calls[0] as [string, { params: { query: Record<string, unknown> } }]
    expect(init.params.query).toMatchObject({ figures_only: true })
  })

  it('detail z Moje figúrky nesie from=minifigs, zo Zbierky nie', () => {
    const store = useFilterStore()
    expect(store.detailQuery()).toEqual({})

    store.setSection('figures')
    expect(store.detailQuery()).toEqual({ from: 'minifigs' })
  })

  it('prepnutie sekcie zahodí filter a počty druhej sekcie', () => {
    const store = useFilterStore()
    store.filters.theme = ['Icons']
    store.facets = { total: 3 } as never

    store.setSection('figures')

    expect(store.filters.theme).toEqual([])
    expect(store.facets).toBeNull()
    expect(store.sectionQuery()).not.toHaveProperty('theme')
  })
})
