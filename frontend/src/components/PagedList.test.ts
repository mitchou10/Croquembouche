import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import PagedList from './PagedList.vue'

const items = (n: number) => Array.from({ length: n }, (_, i) => ({ id: i + 1, name: `Carte ${i + 1}` }))

// jsdom has no layout: what the grid's CSS and the window would say is given by hand.
let areaHeight = 0
let resize: () => void = () => {}

function stubLayout(opts: { wide: boolean; height: number }) {
  areaHeight = opts.height
  vi.stubGlobal('matchMedia', () => ({ matches: opts.wide, addEventListener() {}, removeEventListener() {} }))
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        resize = callback
      }
      observe() {}
      disconnect() {}
    },
  )
  vi.spyOn(window, 'getComputedStyle').mockReturnValue({
    gridTemplateColumns: '200px 200px 200px',
    gridAutoRows: '200px',
    rowGap: '16px',
  } as CSSStyleDeclaration)
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockImplementation(() => areaHeight)
}

async function mountList(count = 10, props: Record<string, unknown> = {}) {
  const wrapper = mount(PagedList, {
    props: { items: items(count), itemKey: (i: { id: number }) => i.id, noun: 'carte', ...props },
    slots: {
      item: (slot: { item: { name: string } }) => h('div', { class: 'card' }, slot.item.name),
      empty: () => h('p', { class: 'empty' }, 'Rien ici'),
    },
  })
  await flushPromises()
  return wrapper
}

const shown = (w: ReturnType<typeof mount>) => w.findAll('.card').map((c) => c.text())
const pager = (w: ReturnType<typeof mount>) => w.find('[data-testid="pager-count"]').text()

describe('PagedList', () => {
  beforeEach(() => stubLayout({ wide: true, height: 440 })) // two rows of three
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows as many cards per page as fit, and pages through the rest', async () => {
    const wrapper = await mountList(10)
    expect(shown(wrapper)).toEqual(['Carte 1', 'Carte 2', 'Carte 3', 'Carte 4', 'Carte 5', 'Carte 6'])
    expect(pager(wrapper)).toBe('1 / 2')
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(shown(wrapper)).toEqual(['Carte 7', 'Carte 8', 'Carte 9', 'Carte 10'])
    expect(pager(wrapper)).toBe('2 / 2')
    expect(wrapper.get('button[title="Page suivante"]').attributes('disabled')).toBeDefined()
    await wrapper.get('button[title="Page précédente"]').trigger('click')
    expect(shown(wrapper)[0]).toBe('Carte 1')
  })

  it('has fewer cards per page in a smaller window, and more in a bigger one', async () => {
    const wrapper = await mountList(10)
    areaHeight = 220 // one row
    resize()
    await nextTick()
    expect(shown(wrapper)).toHaveLength(3)
    expect(pager(wrapper)).toBe('1 / 4')
    areaHeight = 880 // four rows
    resize()
    await nextTick()
    expect(shown(wrapper)).toHaveLength(10)
    expect(wrapper.find('[data-testid="pager-count"]').exists()).toBe(false) // one page: no pager
  })

  it('keeps the card that was at the top on the page shown when the window is resized', async () => {
    const wrapper = await mountList(10)
    await wrapper.get('button[title="Page suivante"]').trigger('click') // Carte 7 on top
    areaHeight = 220 // three per page
    resize()
    await nextTick()
    expect(shown(wrapper)).toContain('Carte 7')
    expect(pager(wrapper)).toBe('3 / 4') // 7 is the first of the third page of three
    areaHeight = 880 // everything on one page
    resize()
    await nextTick()
    expect(shown(wrapper)).toContain('Carte 7')
  })

  it('goes back to the first page when the reset key changes', async () => {
    const wrapper = await mountList(10, { resetKey: 'a' })
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(shown(wrapper)[0]).toBe('Carte 7')
    await wrapper.setProps({ resetKey: 'b' })
    expect(shown(wrapper)[0]).toBe('Carte 1')
  })

  it('stays on a page that still exists when there are fewer cards', async () => {
    const wrapper = await mountList(10)
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    await wrapper.setProps({ items: items(4) }) // the second page is gone
    expect(shown(wrapper)).toEqual(['Carte 1', 'Carte 2', 'Carte 3', 'Carte 4'])
  })

  it('counts the cards, in the singular and in the plural, with what follows', async () => {
    const total = async (n: number, props = {}) => (await mountList(n, props)).get('[data-testid="list-total"]').text()
    expect(await total(1)).toBe('1 carte')
    expect(await total(10)).toBe('10 cartes')
    expect(await total(4, { suffix: ' au total' })).toBe('4 cartes au total')
  })

  it('says so when there is nothing to show', async () => {
    const wrapper = await mountList(0)
    expect(wrapper.get('.empty').text()).toBe('Rien ici')
    expect(wrapper.find('.paged__grid').exists()).toBe(false)
    expect(wrapper.get('[data-testid="list-total"]').text()).toBe('0 carte')
  })

  it('measures once the cards appear after an empty list', async () => {
    const wrapper = await mountList(0)
    await wrapper.setProps({ items: items(10) })
    await flushPromises()
    expect(shown(wrapper)).toHaveLength(6)
  })

  it('hands the sizes it was given to the CSS of the grid', async () => {
    const wrapper = await mountList(3, { minCard: '15rem', rowHeight: '5rem' })
    const style = wrapper.get('.paged__grid').attributes('style')
    expect(style).toContain('--min-card: 15rem')
    expect(style).toContain('--row-height: 5rem')
  })
})

describe('PagedList without a layout to measure', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows six per page on a narrow screen, where the page scrolls as usual', async () => {
    stubLayout({ wide: false, height: 440 })
    const wrapper = await mountList(10)
    expect(shown(wrapper)).toHaveLength(6)
  })

  it('shows six per page when there is nothing to measure yet', async () => {
    stubLayout({ wide: true, height: 0 })
    const wrapper = await mountList(10)
    expect(shown(wrapper)).toHaveLength(6)
  })
})
