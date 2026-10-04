import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import TimeField from './TimeField.vue'

enableAutoUnmount(afterEach)

describe('Časové pole', () => {
  it('pohyb ručičky nič neuloží, až OK pošle nový čas raz', async () => {
    const wrapper = mount(TimeField, {
      props: { modelValue: '07:00' },
      global: { renderStubDefaultSlot: true, stubs: { VMenu: { template: '<div><slot name="activator" :props="{}" /><slot /></div>' } } },
    })
    const vm = wrapper.vm as unknown as { open: boolean, draft: string, confirm: () => void }
    vm.open = true
    await wrapper.vm.$nextTick()

    vm.draft = '08:00'
    vm.draft = '08:15'
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()

    vm.confirm()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:modelValue')).toEqual([['08:15']])
  })

  it('zatvorenie bez zmeny nič nepošle', async () => {
    const wrapper = mount(TimeField, {
      props: { modelValue: '07:00' },
      global: { renderStubDefaultSlot: true, stubs: { VMenu: { template: '<div><slot name="activator" :props="{}" /><slot /></div>' } } },
    })
    const vm = wrapper.vm as unknown as { open: boolean }
    vm.open = true
    await wrapper.vm.$nextTick()
    vm.open = false
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
