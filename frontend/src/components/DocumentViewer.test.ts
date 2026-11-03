import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DocumentViewer from './DocumentViewer.vue'

const document = { name: 'scan.png', type: 'image/png', url: 'blob:scan' }

// jsdom has no layout and no ResizeObserver: the parent's size is pushed by hand.
function mountFitted(available: { width: number; height: number }, natural: { width: number; height: number }) {
  let notify: (size: { width: number; height: number }) => void = () => {}
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: (entries: { contentRect: { width: number; height: number } }[]) => void) {
        notify = (size) => callback([{ contentRect: size }])
      }
      observe() {}
      disconnect() {}
    },
  )
  const wrapper = mount(DocumentViewer, { props: { document, fit: true } })
  const img = wrapper.get('img')
  Object.defineProperty(img.element, 'naturalWidth', { value: natural.width })
  Object.defineProperty(img.element, 'naturalHeight', { value: natural.height })
  return { wrapper, img, notify: () => notify(available) }
}

describe('DocumentViewer fit', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shrinks to the height that is available, keeping the ratio', async () => {
    const { wrapper, img, notify } = mountFitted({ width: 400, height: 200 }, { width: 100, height: 100 })
    await img.trigger('load')
    notify()
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-testid="document-stage"]').attributes('style')).toContain('width: 200px; height: 200px')
  })

  it('shrinks to the width that is available when the space is narrow and tall', async () => {
    const { wrapper, img, notify } = mountFitted({ width: 100, height: 400 }, { width: 200, height: 100 })
    await img.trigger('load')
    notify()
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-testid="document-stage"]').attributes('style')).toContain('width: 100px; height: 50px')
  })

  it('leaves the size alone until both the image and the space are known', async () => {
    const { wrapper, img, notify } = mountFitted({ width: 400, height: 200 }, { width: 100, height: 100 })
    notify()
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-testid="document-stage"]').attributes('style')).toBeUndefined()
    await img.trigger('load')
    expect(wrapper.get('[data-testid="document-stage"]').attributes('style')).toBeDefined()
  })

  it('does not touch the size without the fit prop', async () => {
    const wrapper = mount(DocumentViewer, { props: { document } })
    await wrapper.get('img').trigger('load')
    expect(wrapper.get('[data-testid="document-stage"]').attributes('style')).toBeUndefined()
  })
})
