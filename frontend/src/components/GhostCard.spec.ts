import type * as Client from '@/api/client'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import { VBtn } from 'vuetify/components/VBtn'
import { VCard } from 'vuetify/components/VCard'
import { VChip } from 'vuetify/components/VChip'
import i18n from '@/plugins/i18n'
import GhostCard from './GhostCard.vue'

const post = vi.fn(async () => ({ data: {}, error: undefined }))

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: { POST: (...args: unknown[]) => post(...(args as [])) },
}))

enableAutoUnmount(afterEach)

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe (): void {}
    unobserve (): void {}
    disconnect (): void {}
  } as unknown as typeof ResizeObserver
})

const CATALOG = { catalog_num: '71049-4', name: 'McLaren', kind: 'set', image_url: null } as never

async function mountCard (to?: unknown) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/set/:num', name: 'set-detail', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  const wrapper = mount(GhostCard, {
    props: { catalog: CATALOG, to: to as never },
    global: {
      plugins: [i18n, createPinia(), router, createVuetify({ components: { VBtn, VCard, VChip } })],
      stubs: { SetImage: true, PurchaseDialog: true },
    },
  })
  return { wrapper, router }
}

describe('karta chýbajúcej figúrky', () => {
  it('s cieľom vedie celá karta na detail, kde sa dá overiť cena', async () => {
    i18n.global.locale.value = 'sk'
    const { wrapper } = await mountCard({ name: 'set-detail', params: { num: '71049-4' }, query: { from: 'minifigs' } })

    expect(wrapper.find('a').attributes('href')).toBe('/set/71049-4?from=minifigs')
  })

  it('tlačidlo na karte (Pridať do Chcem) detail neotvorí', async () => {
    i18n.global.locale.value = 'sk'
    const { wrapper, router } = await mountCard({ name: 'set-detail', params: { num: '71049-4' } })

    const wish = wrapper.findAll('button').find(b => b.text().includes('Chcem'))!
    await wish.trigger('click')
    await flushPromises()

    expect(post).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/')
  })
})
