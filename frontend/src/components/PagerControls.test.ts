import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PagerControls from './PagerControls.vue'

const mountPager = (props: Record<string, unknown>) =>
  mount(PagerControls, { props: { modelValue: 0, count: 3, noun: 'Entité', ...props } })

describe('PagerControls', () => {
  it('says where one is, from 1', () => {
    expect(mountPager({ modelValue: 1 }).get('[data-testid="pager-count"]').text()).toBe('2 / 3')
    expect(mountPager({ count: 0 }).get('[data-testid="pager-count"]').text()).toBe('0')
  })

  it('names its buttons for what is paged, in the feminine by default', () => {
    const wrapper = mountPager({})
    expect(wrapper.findAll('button').map((b) => b.attributes('title'))).toEqual(['Entité précédente', 'Entité suivante'])
  })

  it('names them in the masculine when the noun is', () => {
    const wrapper = mountPager({ noun: 'Élément', masculine: true })
    expect(wrapper.findAll('button').map((b) => b.attributes('title'))).toEqual(['Élément précédent', 'Élément suivant'])
    expect(wrapper.text()).toContain('Élément suivant')
  })

  it('cannot go before the first or after the last', () => {
    const first = mountPager({ modelValue: 0 })
    expect(first.findAll('button')[0].attributes('disabled')).toBeDefined()
    expect(first.findAll('button')[1].attributes('disabled')).toBeUndefined()
    const last = mountPager({ modelValue: 2 })
    expect(last.findAll('button')[0].attributes('disabled')).toBeUndefined()
    expect(last.findAll('button')[1].attributes('disabled')).toBeDefined()
  })

  it('moves one by one', async () => {
    const wrapper = mountPager({ modelValue: 1, 'onUpdate:modelValue': (v: number) => wrapper.setProps({ modelValue: v }) })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('3 / 3')
    await wrapper.findAll('button')[0].trigger('click')
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 3')
  })

  it('has room for buttons of its own after its own', () => {
    const wrapper = mount(PagerControls, { props: { modelValue: 0, count: 2, noun: 'Page' }, slots: { default: '<button class="mine">Ajouter</button>' } })
    expect(wrapper.get('.mine').text()).toBe('Ajouter')
  })
})
