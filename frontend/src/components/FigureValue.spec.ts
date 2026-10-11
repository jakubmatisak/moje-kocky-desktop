import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createVuetify } from 'vuetify'
import i18n from '@/plugins/i18n'
import FigureValue from './FigureValue.vue'

function render (props: Record<string, unknown>) {
  i18n.global.locale.value = 'sk'
  return mount(FigureValue, { props, global: { plugins: [i18n, createVuetify()] } })
}

const text = (w: ReturnType<typeof render>) => w.text().replace(/\s+/g, ' ')

describe('sumy vo Figúrkach ako na karte setu', () => {
  it('kúpené, hodnota, percento a dátum ceny', () => {
    const w = render({ purchase: '7.00', value: '10.50', profitPct: 50, priceAt: '2026-09-03T12:00:00Z' })
    expect(text(w)).toMatch(/Kúpené ?7,00 €/)
    expect(text(w)).toMatch(/Hodnota ?10,50 €/)
    expect(text(w)).toContain('+50 %')
    expect(text(w)).toContain('cena z 3. 9. 2026')
  })

  it('bez ceny pomlčka, nie nula; duplikáty povie', () => {
    const w = render({ purchase: '7.00', value: null, profitPct: null, duplicates: 2 })
    expect(text(w)).toContain('cena neznáma')
    expect(text(w)).not.toContain('0,00 €')
    expect(w.find('[data-test="figure-duplicates"]').text()).toContain('2 duplikáty')
  })

  it('figúrka, ktorú nemám: štítok a cena na trhu', () => {
    const w = render({ missing: true, marketNow: '9.00', marketNowAt: '2026-09-01T12:00:00Z' })
    expect(text(w)).toContain('Nemám, len cena')
    expect(text(w)).toMatch(/Trh teraz ?9,00 €/)
    expect(w.find('[data-test="figure-value"]').exists()).toBe(false)
  })
})
