import { describe, expect, it } from 'vitest'
import i18n from '@/plugins/i18n'
import { autoLastLabel } from './autoRefresh'

const t = (key: string, named?: Record<string, unknown>) => i18n.global.t(key, named ?? {})
const NOW = new Date(2026, 9, 4, 9, 0)

describe('automatická obnova: posledný beh', () => {
  it('dnes s časom bez úvodnej nuly a počtom', () => {
    i18n.global.locale.value = 'sk'
    expect(autoLastLabel({ at: '2026-10-04T07:02', updated: 23, outcome: 'ok', complete: true }, t, NOW))
      .toBe('Naposledy automaticky: dnes 7:02, obnovené ceny: 23')
  })

  it('iný deň s dátumom a problém slovom', () => {
    i18n.global.locale.value = 'sk'
    expect(autoLastLabel({ at: '2026-10-02T07:00', updated: 0, outcome: 'quota', complete: true }, t, NOW))
      .toBe('Naposledy automaticky: 2. 10. 7:00, denný limit bol minutý (obnovené ceny: 0)')
  })

  it('bez behu nič', () => {
    expect(autoLastLabel(null, t, NOW)).toBeNull()
  })
})
