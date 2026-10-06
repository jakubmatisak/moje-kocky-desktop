import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { useChartRange } from './useChartRange'

describe('výber obdobia grafu', () => {
  it('rýchla voľba nastaví od–do, pole od–do prepne na vlastné obdobie', async () => {
    const remembered: string[] = []
    const range = useChartRange('all', value => remembered.push(value))
    expect([range.from.value, range.to.value]).toEqual([null, null])

    range.preset.value = '6m'
    await nextTick()
    expect(range.from.value).not.toBeNull()
    expect(remembered).toEqual(['all', '6m'])

    range.setEdge('from', '2026-03-01')
    await nextTick()
    expect(range.preset.value).toBe('custom')
    expect(range.fromInput.value).toBe('2026-03-01')
    expect(remembered).toEqual(['all', '6m'])
  })

  it('opätovné kliknutie na zvolenú voľbu ju nezruší', async () => {
    const range = useChartRange('1y')
    range.preset.value = null as never
    await nextTick()
    expect(range.preset.value).toBe('1y')
  })
})
