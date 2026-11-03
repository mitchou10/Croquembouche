import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import InfoTip from './InfoTip.vue'

const mountTip = () =>
  mount(InfoTip, { props: { label: 'Définition du type Date' }, slots: { default: 'Une date.' }, attachTo: document.body })

describe('InfoTip', () => {
  it('is closed at first, with a button that says what it is for', () => {
    const wrapper = mountTip()
    const button = wrapper.get('button')
    expect(button.attributes('aria-label')).toBe('Définition du type Date')
    expect(button.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('[role="note"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('opens and closes with its button, and points the button at the panel', async () => {
    const wrapper = mountTip()
    await wrapper.get('button').trigger('click')
    expect(wrapper.get('button').attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('[role="note"]').text()).toBe('Une date.')
    expect(wrapper.get('button').attributes('aria-controls')).toBe(wrapper.get('[role="note"]').attributes('id'))
    await wrapper.get('button').trigger('click')
    expect(wrapper.find('[role="note"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('closes with Escape', async () => {
    const wrapper = mountTip()
    await wrapper.get('button').trigger('click')
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="note"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('closes on a click elsewhere, but not on a click inside', async () => {
    const wrapper = mountTip()
    await wrapper.get('button').trigger('click')
    wrapper.get('[role="note"]').element.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="note"]').exists()).toBe(true)
    document.body.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="note"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('lines the panel up with the end of the button on request', async () => {
    const wrapper = mount(InfoTip, { props: { label: 'x', align: 'end' }, slots: { default: 'y' } })
    // jsdom has no layout: a panel that fits, away from both edges.
    const spy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ left: 100, right: 420 } as DOMRect)
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="note"]').classes()).toContain('info-tip__panel--end')
    spy.mockRestore()
    wrapper.unmount()
  })

  it('turns round when it would go past the edge of the window, and back when that is no better', async () => {
    const rect = (left: number, right: number) => ({ left, right, top: 0, bottom: 0, width: right - left, height: 0 }) as DOMRect
    const wrapper = mount(InfoTip, { props: { label: 'x' }, slots: { default: 'y' }, attachTo: document.body })
    const spy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect')
    spy.mockReturnValue(rect(window.innerWidth - 100, window.innerWidth + 220)) // starts at the button, runs off the right
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="note"]').classes()).toContain('info-tip__panel--end')
    await wrapper.get('button').trigger('click') // closed
    spy.mockReturnValue(rect(40, 360)) // fits
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="note"]').classes()).not.toContain('info-tip__panel--end')
    spy.mockRestore()
    wrapper.unmount()
  })

  it('stops listening once gone', async () => {
    const wrapper = mountTip()
    await wrapper.get('button').trigger('click')
    wrapper.unmount()
    // Nothing left to react to Escape or a click: this must simply not throw.
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    document.body.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  })
})
