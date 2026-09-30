import { RouterLinkStub, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import i18n from '@/plugins/i18n'
import FiguresElsewhere from './FiguresElsewhere.vue'

function render (count: number) {
  return shallowMount(FiguresElsewhere, {
    props: { count },
    global: { plugins: [i18n], stubs: { RouterLink: RouterLinkStub }, config: { warnHandler: () => {} } },
  })
}

describe('Zbierka: figúrky zo sérií sú vo Figúrkach', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'sk'
  })

  it('je to nenápadný riadok s textovým odkazom, nie upozornenie ani tlačidlo', () => {
    const line = render(77)
    expect(line.find('v-alert').exists()).toBe(false)
    expect(line.find('v-btn').exists()).toBe(false)
    expect(line.find('v-icon').exists()).toBe(true)

    const link = line.findComponent(RouterLinkStub)
    // Pomenovaná trasa: desktop má hash router, pevná cesta by tam neviedla.
    expect(link.props('to')).toEqual({ name: 'minifigs' })
    expect(link.text()).toBe('Otvoriť Figúrky')
  })

  it('povie koľko, v správnom tvare', () => {
    expect(render(1).text()).toContain('1 figúrka zo série je vo Figúrkach')
    expect(render(3).text()).toContain('3 figúrky zo sérií sú vo Figúrkach')
    expect(render(77).text()).toContain('77 figúrok zo sérií je vo Figúrkach')
  })

  it('po anglicky', () => {
    i18n.global.locale.value = 'en'
    expect(render(1).text()).toContain('1 series minifigure is in Minifigures')
    expect(render(5).text()).toContain('5 series minifigures are in Minifigures')
    expect(render(5).findComponent(RouterLinkStub).text()).toBe('Open Minifigures')
  })

  it('bez figúrok nie je čo hlásiť', () => {
    expect(render(0).text()).toBe('')
  })
})
