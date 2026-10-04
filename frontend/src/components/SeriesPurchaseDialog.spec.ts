import type * as Client from '@/api/client'
import { enableAutoUnmount, flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/plugins/i18n'
import SeriesPurchaseDialog from './SeriesPurchaseDialog.vue'

const posts: Array<{ path: string, body: { members: Array<{ catalog_num: string }>, purchase_total_eur: string | null } }> = []

vi.mock('@/api/client', async original => ({
  ...(await original<typeof Client>()),
  api: {
    GET: async () => ({ data: {} }),
    POST: async (path: string, options: { body: never }) => {
      posts.push({ path, body: options.body })
      return { data: [] }
    },
  },
}))

enableAutoUnmount(afterEach)

function member (num: string, owned: number) {
  return { catalog: { catalog_num: num, name: num, image_url: null }, owned, wanted: false }
}

const SERIES = { series_num: '71052', name: 'Series 27', image_url: null, total: 3 }
const MEMBERS = [member('71052-1', 1), member('71052-2', 0), member('71052-3', 0)]

async function mountDialog (props: Record<string, unknown>) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = shallowMount(SeriesPurchaseDialog, {
    props: { modelValue: false, series: SERIES as never, members: MEMBERS as never, ...props },
    global: { plugins: [i18n, pinia], renderStubDefaultSlot: true },
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

describe('Kúpil som: viac figúrok naraz', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
    posts.length = 0
  })

  it('vybrané figúrky, chýbajúca aj duplikát, sa pridajú jednou sumou', async () => {
    const wrapper = await mountDialog({ chosen: [MEMBERS[0], MEMBERS[2]] })
    const vm = wrapper.vm as unknown as { total: string, save: () => Promise<void> }
    vm.total = '9'
    await vm.save()
    await flushPromises()

    expect(posts).toHaveLength(1)
    expect(posts[0]?.path).toBe('/items/bulk')
    expect(posts[0]?.body.members.map(m => m.catalog_num)).toEqual(['71052-1', '71052-3'])
    expect(posts[0]?.body.purchase_total_eur).toBe('9')
  })

  it('bez výberu ostáva Mám všetky: len chýbajúce', async () => {
    const wrapper = await mountDialog({})
    const vm = wrapper.vm as unknown as { save: () => Promise<void> }
    await vm.save()
    await flushPromises()

    expect(posts[0]?.body.members.map(m => m.catalog_num)).toEqual(['71052-2', '71052-3'])
  })
})
