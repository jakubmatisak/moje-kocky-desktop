import { enableAutoUnmount, shallowMount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { Line } from 'vue-chartjs'
import { createVuetify } from 'vuetify'
import i18n from '@/plugins/i18n'
import PriceHistoryChart from './PriceHistoryChart.vue'

enableAutoUnmount(afterEach)

const POINTS = [
  { captured_at: '2025-01-01T12:00:00Z', avg_price: '10.00' },
  { captured_at: '2025-06-01T12:00:00Z', avg_price: '20.00' },
  { captured_at: '2026-01-01T12:00:00Z', avg_price: '30.00' },
]
const EVENTS = [
  { day: '2025-02-01', kind: 'buy', count: 1, amount: '9.00' },
  { day: '2025-12-01', kind: 'buy', count: 2, amount: '40.00' },
]

function mountChart () {
  return shallowMount(PriceHistoryChart, {
    props: { newPoints: POINTS as never, usedPoints: [], purchase: 25, events: EVENTS, periods: true },
    global: { plugins: [i18n, createVuetify()] },
  })
}

type Dataset = { label: string, data: { x: number, y: number }[] }

function datasets (wrapper: ReturnType<typeof mountChart>): Dataset[] {
  return (wrapper.findComponent(Line).props('data') as { datasets: Dataset[] }).datasets
}

describe('graf ceny s obdobím', () => {
  it('od–do ukáže len obdobie: krivku orezanú na okraji a nákupy v ňom', async () => {
    i18n.global.locale.value = 'sk'
    const wrapper = mountChart()
    expect(datasets(wrapper)[0]!.data).toHaveLength(3)

    const [fromField] = wrapper.findAllComponents({ name: 'DateField' })
    fromField!.vm.$emit('update:modelValue', '2025-09-01')
    await wrapper.vm.$nextTick()

    const [prices, , bought] = datasets(wrapper)
    const start = new Date('2025-09-01T00:00:00').getTime()
    expect(prices!.data[0]!.x).toBe(start)
    expect(prices!.data.at(-1)!.y).toBe(30)
    expect(prices!.data).toHaveLength(2)
    expect(bought!.data).toHaveLength(1)
  })

  it('bez periods sa výber obdobia neukáže', () => {
    const wrapper = shallowMount(PriceHistoryChart, {
      props: { newPoints: POINTS as never, usedPoints: [], purchase: null },
      global: { plugins: [i18n, createVuetify()] },
    })
    expect(wrapper.findAllComponents({ name: 'DateField' })).toHaveLength(0)
  })
})
