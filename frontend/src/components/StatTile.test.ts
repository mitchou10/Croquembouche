import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatTile from './StatTile.vue'

describe('StatTile', () => {
  it('is only a figure, which cannot be pressed', async () => {
    const wrapper = mount(StatTile, { props: { value: 3, label: 'Vues' } })
    expect(wrapper.element.tagName).toBe('DIV')
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('is a button that says it was chosen, and whether its choice is on', async () => {
    const wrapper = mount(StatTile, { props: { value: 3, label: 'En cours', selectable: true, selected: false } })
    expect(wrapper.element.tagName).toBe('BUTTON')
    expect(wrapper.attributes('aria-pressed')).toBe('false')
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toHaveLength(1)
    await wrapper.setProps({ selected: true })
    expect(wrapper.attributes('aria-pressed')).toBe('true')
  })

  it('has no pressed state when it does not say if it is on', () => {
    const wrapper = mount(StatTile, { props: { value: 3, label: 'Utilisations', selectable: true } })
    expect(wrapper.attributes('aria-pressed')).toBeUndefined()
  })
})
