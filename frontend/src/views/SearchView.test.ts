import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../router'
import SearchView from './SearchView.vue'

async function mountView() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  const wrapper = mount(SearchView, { global: { plugins: [VueDsfr, router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

async function send(wrapper: Awaited<ReturnType<typeof mountView>>, file: File) {
  const input = wrapper.get('[data-testid="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

// jsdom has no pointer events: a mouse event of the same name is what the page listens to.
const pointer = (target: Element | Window, type: string, x = 0, y = 0) =>
  target.dispatchEvent(new MouseEvent(type, { button: 0, clientX: x, clientY: y, bubbles: true }))

const png = (name = 'facture.png') => new File([new Uint8Array(10)], name, { type: 'image/png' })

describe('the search page', () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()
    document.body.innerHTML = ''
  })

  it('asks for a document first, and nothing else', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="graph"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="again"]').exists()).toBe(false)
  })

  it('draws the document and its neighbours as a graph, and lists them beside it', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(false)
    // The document and six neighbours, each a picture.
    expect(wrapper.findAll('[data-testid="graph"] image')).toHaveLength(7)
    expect(wrapper.findAll('[data-testid="neighbours"] li')).toHaveLength(6)
    expect(wrapper.get('[data-testid="node-query"]').attributes('aria-label')).toBe('Document envoyé : facture.png')
  })

  it('refuses what is not an image or a PDF, and what is too big', async () => {
    const wrapper = await mountView()
    await send(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    expect(wrapper.get('[data-testid="fault"]').text()).toContain('Seuls les images')
    expect(wrapper.find('[data-testid="graph"]').exists()).toBe(false)
    await send(wrapper, new File([new Uint8Array(21 * 1024 * 1024)], 'gros.png', { type: 'image/png' }))
    expect(wrapper.get('[data-testid="fault"]').text()).toContain('trop lourd')
  })

  it('chooses a neighbour from the list, and from the graph', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    await wrapper.get('[data-testid="neighbour-n2"]').trigger('click')
    expect(wrapper.get('[data-testid="neighbour-n2"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="node-n2"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="selected"]').text()).toContain('ressemble à')

    await wrapper.get('[data-testid="node-n3"]').trigger('keydown', { key: 'Enter' })
    expect(wrapper.get('[data-testid="node-n3"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="node-n2"]').attributes('aria-pressed')).toBe('false')

    await wrapper.get('[data-testid="node-n3"]').trigger('keydown', { key: 'Enter' }) // again: let go of it
    expect(wrapper.find('[data-testid="selected"]').exists()).toBe(false)
  })

  it('chooses a node with a click that hardly moves it', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    const node = wrapper.get('[data-testid="node-n1"]')
    pointer(node.element, 'pointerdown', 10, 10)
    pointer(window, 'pointerup', 10, 10)
    await flushPromises()
    expect(wrapper.get('[data-testid="node-n1"]').attributes('aria-pressed')).toBe('true')
  })

  it('moves a node that is dragged, and does not choose it', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    const node = wrapper.get('[data-testid="node-n1"]')
    const before = node.attributes('transform')
    pointer(node.element, 'pointerdown', 0, 0)
    pointer(window, 'pointermove', 120, 90)
    pointer(window, 'pointerup', 120, 90)
    await flushPromises()
    expect(wrapper.get('[data-testid="node-n1"]').attributes('transform')).not.toBe(before)
    expect(wrapper.get('[data-testid="node-n1"]').attributes('aria-pressed')).toBe('false')
  })

  it('searches again with another number of neighbours', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    const k = wrapper.get('[data-testid="k"]')
    ;(k.element as HTMLInputElement).value = '3'
    await k.trigger('change')
    expect(wrapper.findAll('[data-testid="neighbours"] li')).toHaveLength(3)
  })

  it('starts again from the dropzone', async () => {
    const wrapper = await mountView()
    await send(wrapper, png())
    await wrapper.get('[data-testid="again"]').trigger('click')
    expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="graph"]').exists()).toBe(false)
  })

  it('is reached from the sidebar route', () => {
    expect(routes.flatMap((r) => r.children ?? []).some((r) => r.name === 'search' && r.path === 'recherche')).toBe(true)
  })
})
