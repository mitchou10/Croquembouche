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

describe('DocumentViewer rectangle editing', () => {
  const rectZone = {
    page: 1,
    points: [
      { x: 0.2, y: 0.2 },
      { x: 0.6, y: 0.2 },
      { x: 0.6, y: 0.5 },
      { x: 0.2, y: 0.5 },
    ],
  }
  const entities = [{ id: 'e1', name: 'Date', definition: '', type: 'text', examples: [], zone: rectZone }]
  const props = { document, entities: entities as never, highlightId: 'e1', editable: true }

  // jsdom has no layout: the stage is given a 100 x 100 box so that a pixel is a percent.
  function stageOf(wrapper: ReturnType<typeof mount>) {
    wrapper.get('[data-testid="document-stage"]').element.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 }) as DOMRect
  }

  // VTU cannot set clientX on a mouse event, and jsdom has no PointerEvent: the events are built by hand.
  async function fire(wrapper: ReturnType<typeof mount>, selector: string, type: string, x = 0, y = 0) {
    wrapper.get(selector).element.dispatchEvent(new MouseEvent(type, { bubbles: true, clientX: x, clientY: y }))
    await wrapper.vm.$nextTick()
  }

  it('shows handles on the rectangle of the entity on show, and only when editable', () => {
    expect(mount(DocumentViewer, { props }).findAll('[data-testid^="rect-handle-"]')).toHaveLength(8)
    expect(mount(DocumentViewer, { props: { ...props, editable: false } }).find('[data-testid="rect-edit"]').exists()).toBe(false)
    expect(mount(DocumentViewer, { props: { ...props, drawing: true } }).find('[data-testid="rect-edit"]').exists()).toBe(false)
  })

  it('emits the resized zone while a handle is dragged', async () => {
    const wrapper = mount(DocumentViewer, { props })
    stageOf(wrapper)
    await fire(wrapper, '[data-testid="rect-handle-e"]', 'pointerdown', 60, 35)
    await fire(wrapper, '[data-testid="document-viewport"]', 'pointermove', 80, 35)
    const [id, zone] = wrapper.emitted('update')!.at(-1)! as [string, { points: { x: number; y: number }[] }]
    expect(id).toBe('e1')
    expect(Math.max(...zone.points.map((p) => p.x))).toBeCloseTo(0.8)
    expect(Math.min(...zone.points.map((p) => p.x))).toBeCloseTo(0.2)
  })

  it('stops following the pointer once it is released', async () => {
    const wrapper = mount(DocumentViewer, { props })
    stageOf(wrapper)
    await fire(wrapper, '[data-testid="rect-edit"]', 'pointerdown', 30, 30)
    await fire(wrapper, '[data-testid="document-viewport"]', 'pointerup')
    await fire(wrapper, '[data-testid="document-viewport"]', 'pointermove', 50, 50)
    expect(wrapper.emitted('update')).toBeUndefined()
  })

  it('asks to remove the zone on Delete', async () => {
    const wrapper = mount(DocumentViewer, { props })
    await wrapper.get('[data-testid="rect-edit"]').trigger('keydown', { key: 'Delete' })
    expect(wrapper.emitted('remove')).toEqual([['e1']])
  })

  it('leaves a polygon alone', () => {
    const polygon = { page: 1, points: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }] }
    const wrapper = mount(DocumentViewer, { props: { ...props, entities: [{ ...entities[0], zone: polygon }] as never } })
    expect(wrapper.find('[data-testid="rect-edit"]').exists()).toBe(false)
  })
})
