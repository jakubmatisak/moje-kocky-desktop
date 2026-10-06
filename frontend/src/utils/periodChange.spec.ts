import { describe, expect, it } from 'vitest'
import { periodChange } from './periodChange'

function p (day: string, invested: number, value: number, proceeds = 0) {
  return { day, invested: String(invested), market_value: String(value), proceeds: String(proceeds) }
}

const ms = (day: string): number => new Date(`${day}T00:00:00`).getTime()

describe('zisk za zvolené obdobie', () => {
  it('bez nákupov: zmena nerealizovaného zisku a zisk pred obdobím a teraz', () => {
    const points = [p('2026-01-01', 100, 110), p('2026-04-01', 100, 120), p('2026-10-01', 100, 150)]

    const change = periodChange(points, ms('2026-04-01'), ms('2026-10-06'))

    expect(change).toMatchObject({ startDay: '2026-04-01', endDay: '2026-10-01', change: 30, pctStart: 20, pctEnd: 50 })
    expect(change?.pct).toBeCloseTo(25)
  })

  it('dokúpené peniaze nie sú zisk, ale počítajú sa do základu', () => {
    const points = [p('2026-04-01', 100, 120), p('2026-10-01', 200, 260)]

    const change = periodChange(points, ms('2026-04-01'), ms('2026-10-06'))

    expect(change?.change).toBe(40)
    expect(change?.pct).toBeCloseTo(40 / 220 * 100)
  })

  it('obdobie pred začiatkom histórie berie prvý bod; predaje v období zvlášť', () => {
    const points = [p('2026-03-01', 100, 100), p('2026-10-01', 50, 80, 70)]

    const change = periodChange(points, ms('2025-10-01'), null)

    expect(change).toMatchObject({ startDay: '2026-03-01', sold: 70 })
  })

  it('jeden bod alebo celá história bez obdobia nič', () => {
    expect(periodChange([p('2026-03-01', 100, 100)], ms('2026-01-01'), null)).toBeNull()
    expect(periodChange([p('2026-03-01', 100, 100), p('2026-04-01', 100, 120)], null, null)).toBeNull()
  })
})
