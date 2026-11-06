import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ZoneCrop from './ZoneCrop.vue'

const document = { name: 'p', type: 'image/png', url: '/page.png' }
const rectangle = [
  { x: 0.1, y: 0.2 },
  { x: 0.5, y: 0.2 },
  { x: 0.5, y: 0.4 },
  { x: 0.1, y: 0.4 },
]
const turned = [
  { x: 0.6, y: 0.1 },
  { x: 0.6, y: 0.5 },
  { x: 0.4, y: 0.5 },
  { x: 0.4, y: 0.1 },
]

/** Mounts the crop and lets the page image load, 1000 by 500 pixels. */
async function loaded(points: { x: number; y: number }[]) {
  const wrapper = mount(ZoneCrop, { props: { document, zone: { page: 1, points } } })
  const img = wrapper.get('img')
  Object.defineProperty(img.element, 'naturalWidth', { value: 1000 })
  Object.defineProperty(img.element, 'naturalHeight', { value: 500 })
  await img.trigger('load')
  return { wrapper, img }
}

describe('ZoneCrop', () => {
  it('cuts out a zone that is straight, by its box', async () => {
    const { wrapper, img } = await loaded(rectangle)
    expect(wrapper.get('.crop__frame').attributes('data-straightened')).toBeUndefined()
    expect(img.attributes('style')).toContain('left: -25%')
    expect(img.attributes('style')).not.toContain('matrix3d')
  })

  it('puts a zone that is turned straight, with a perspective transformation of the page', async () => {
    const { wrapper, img } = await loaded(turned)
    expect(wrapper.get('.crop__frame').attributes('data-straightened')).toBe('')
    expect(img.attributes('style')).toContain('matrix3d(')
    expect(img.attributes('style')).toContain('width: 1000px') // at its own size, then scaled
  })

  it('shows nothing until the page has loaded', () => {
    const wrapper = mount(ZoneCrop, { props: { document, zone: { page: 1, points: turned } } })
    expect(wrapper.get('.crop__frame').attributes('style')).toContain('display: none')
  })
})
