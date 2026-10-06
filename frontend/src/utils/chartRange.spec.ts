import { describe, expect, it } from 'vitest'
import { clipSeries, presetRange } from './chartRange'

const DAY = 86_400_000

describe('obdobie grafu', () => {
  it('krivka sa oreže na obdobie a na okrajoch dopočíta hodnotu z bodov okolo', () => {
    const points = [
      { x: 0, y: 10 },
      { x: 10 * DAY, y: 20 },
      { x: 20 * DAY, y: 40 },
    ]

    expect(clipSeries(points, 5 * DAY, 15 * DAY)).toEqual([
      { x: 5 * DAY, y: 15 },
      { x: 10 * DAY, y: 20 },
      { x: 15 * DAY, y: 30 },
    ])
  })

  it('za poslednou cenou sa krivka nepredlžuje a pred prvou nezačína', () => {
    const points = [
      { x: 10 * DAY, y: 20 },
      { x: 20 * DAY, y: 40 },
    ]

    expect(clipSeries(points, 0, 30 * DAY)).toEqual(points)
    expect(clipSeries(points, null, null)).toEqual(points)
    // Okraj presne na cene: bod sa nezdvojí.
    expect(clipSeries([{ x: 0, y: 5 }, ...points, { x: 30 * DAY, y: 50 }], 10 * DAY, 20 * DAY)).toEqual(points)
  })

  it('obdobie medzi dvoma cenami má aspoň dva dopočítané body', () => {
    const points = [
      { x: 0, y: 10 },
      { x: 10 * DAY, y: 20 },
    ]

    expect(clipSeries(points, 2 * DAY, 4 * DAY)).toEqual([
      { x: 2 * DAY, y: 12 },
      { x: 4 * DAY, y: 14 },
    ])
  })

  it('rýchle voľby sa rátajú od dnes, Všetko je bez hraníc', () => {
    const now = new Date(2026, 9, 6, 15, 30).getTime()

    expect(presetRange('3m', now)).toEqual([new Date(2026, 6, 6).getTime(), now])
    expect(presetRange('ytd', now)).toEqual([new Date(2026, 0, 1).getTime(), now])
    expect(presetRange('all', now)).toEqual([null, null])
  })
})
