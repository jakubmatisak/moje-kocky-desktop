import type * as Client from '@/api/client'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import { VBtn } from 'vuetify/components/VBtn'
import { VCard, VCardActions, VCardText, VCardTitle } from 'vuetify/components/VCard'
import { VCombobox } from 'vuetify/components/VCombobox'
import { VDialog } from 'vuetify/components/VDialog'
import { VSpacer } from 'vuetify/components/VGrid'
import { VList, VListItem } from 'vuetify/components/VList'
import { VMenu } from 'vuetify/components/VMenu'
import { VProgressLinear } from 'vuetify/components/VProgressLinear'
import { VSelect } from 'vuetify/components/VSelect'
import { createSelection } from '@/composables/useSelection'
import i18n from '@/plugins/i18n'
import { useFilterStore } from '@/stores/filters'
import BulkBar from './BulkBar.vue'

const post = vi.fn()

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async () => ({ data: [] }),
    POST: (...args: unknown[]) => post(...args),
  },
}))

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe (): void {}
    unobserve (): void {}
    disconnect (): void {}
  } as unknown as typeof ResizeObserver
  globalThis.visualViewport ??= {
    width: 1024,
    height: 768,
    addEventListener: () => {},
    removeEventListener: () => {},
  } as unknown as VisualViewport
})

let wrapper: ReturnType<typeof mount> | null = null

function button (text: string): HTMLElement {
  const found = [...document.body.querySelectorAll<HTMLElement>('.v-btn, .v-list-item')]
    .find(b => b.textContent?.trim() === text)
  if (!found) {
    throw new Error(`${text} nie je na stránke`)
  }
  return found
}

/** Presunie vybrané kusy do krabice a vráti query, s ktorým sa pýtal server. */
async function moveToBox (props: Record<string, unknown>) {
  const selection = createSelection()
  selection.active.value = true
  selection.toggleItem(11)
  wrapper = mount(BulkBar, {
    attachTo: document.body,
    props: { selection, total: 2, unit: 'pieces', ...props },
    global: {
      plugins: [
        createVuetify({
          components: {
            VBtn, VCard, VCardActions, VCardText, VCardTitle, VCombobox, VDialog,
            VList, VListItem, VMenu, VSelect, VSpacer,
          },
        }),
        i18n,
      ],
    },
  })
  button('Zmeniť').click()
  await flushPromises()
  button('Presunúť do krabice').click()
  await flushPromises()
  button('Pokračovať').click()
  await flushPromises()
  const [[path, options]] = post.mock.calls as [[string, { params: { query: Record<string, unknown> }, body: unknown }]]
  return { path, query: options.params.query, body: options.body }
}

describe('hromadná úprava: rozsah výberu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'sk'
    post.mockReset()
    post.mockResolvedValue({ data: { items: 1, sets: 1 } })
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  it('v Zbierke ide s filtrom Zbierky, teda bez figúrok zo sérií', async () => {
    useFilterStore().filters.theme = ['Icons']
    const { path, query } = await moveToBox({})

    expect(path).toBe('/items/bulk-update')
    expect(query).toMatchObject({ theme: ['Icons'], sets_only: true })
  })

  it('detail série pošle vlastný rozsah: séria, bez rozsahu Zbierky', async () => {
    useFilterStore().filters.theme = ['Icons']
    const { query, body } = await moveToBox({ query: { series: ['71051'] } })

    expect(query).toEqual({ series: ['71051'] })
    expect(body).toMatchObject({ item_ids: [11], dry_run: true })
  })
})

describe('hromadné zmazanie (stránka série)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'sk'
    post.mockReset()
    post.mockResolvedValue({ data: { items: 3, sets: 2 } })
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  function mountDeletable (deletable: boolean) {
    const selection = createSelection({ groups: () => ['71052-1', '71052-2'], explicitAll: true })
    selection.active.value = true
    selection.selectAll()
    wrapper = mount(BulkBar, {
      attachTo: document.body,
      props: { selection, total: 2, unit: 'figures', query: { series: ['71052'] }, deletable },
      global: {
        plugins: [
          createVuetify({
            components: {
              VBtn, VCard, VCardActions, VCardText, VCardTitle, VCombobox, VDialog,
              VList, VListItem, VMenu, VProgressLinear, VSelect, VSpacer,
            },
          }),
          i18n,
        ],
      },
    })
  }

  it('v Zbierke tlačidlo Zmazať nie je', async () => {
    mountDeletable(false)
    await flushPromises()
    expect(() => button('Zmazať')).toThrow()
  })

  it('najprv počet, zmaže až po potvrdení a pošle zoznam figúrok', async () => {
    mountDeletable(true)
    await flushPromises()

    button('Zmazať').click()
    await flushPromises()
    expect(post.mock.calls).toHaveLength(1)
    expect(post.mock.calls[0]?.[0]).toBe('/items/bulk-delete')
    expect(post.mock.calls[0]?.[1]).toMatchObject({
      params: { query: { series: ['71052'] } },
      body: { catalog_nums: ['71052-1', '71052-2'], dry_run: true },
    })
    expect(document.body.textContent).toContain('Zmazať 3 kusy?')

    const confirm = [...document.body.querySelectorAll<HTMLElement>('.v-dialog .v-btn')].find(b => b.textContent?.trim() === 'Zmazať')
    confirm?.click()
    await flushPromises()
    expect(post.mock.calls).toHaveLength(2)
    expect(post.mock.calls[1]?.[1]).toMatchObject({ body: { dry_run: false } })
  })
})
