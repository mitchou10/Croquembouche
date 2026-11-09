import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../App.vue'
import { resetAnalyses } from '../composables/useAnalyses'
import { resetCatalogue, useCatalogue } from '../composables/useCatalogue'
import { resetSearches, useSearches } from '../composables/useSearches'
import { useSession } from '../composables/useSession'
import { uploadDocument } from '../data/api'
import { requireAuth, routes } from '../router'

async function mountAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.beforeEach(requireAuth)
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [VueDsfr, router] }, attachTo: document.body })
  await vi.waitFor(() => expect(wrapper.find('h1').exists()).toBe(true))
  await flushPromises()
  return { wrapper, router }
}

const png = (name = 'facture.png') => new File([new Uint8Array(10)], name, { type: 'image/png' })
const pdf = (name = 'dossier.pdf') => new File([new Uint8Array(10)], name, { type: 'application/pdf' })

async function makeModels() {
  const { create } = useCatalogue()
  const made = []
  for (const [name, type] of [['Facture', 'image/png'], ['Contrat', 'application/pdf'], ['Attestation', 'image/png']] as const) {
    const document = await uploadDocument(new File(['x'], `${name}.x`, { type }))
    made.push(await create({ name, description: '', categories: [], entities: [], pages: [{ page: 2, name: 'Pièces', description: '' }] }, document))
  }
  return made
}

/** Searches, then comes back to the page as a new visit would. */
async function searched(file: File, k = 3) {
  const models = await makeModels()
  const { id } = await useSearches().start(file, k, null)
  resetSearches()
  const page = await mountAt(`/recherche/${id}`)
  await vi.waitFor(() => expect(page.wrapper.find('[data-testid="graph"], [data-testid="running"], [data-testid="failed"]').exists()).toBe(true))
  return { ...page, id, models }
}

describe('the result of a search', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    resetCatalogue()
    resetAnalyses()
    resetSearches()
    useSession().setUser('alice')
  })
  afterEach(() => vi.useRealTimers())

  it('draws the document in the middle and the pages of models that look like it around, with what it consumed', async () => {
    const { wrapper } = await searched(png())
    expect(wrapper.get('[data-testid="title"]').text()).toBe('facture.png')
    expect(wrapper.get('[data-testid="meta"]').text()).toContain('1 page · 3 voisins par page · tous les modèles')
    expect(wrapper.findAll('[data-testid="graph"] [data-testid^="node-page-"]')).toHaveLength(1)
    // Three neighbours at most: the models have four pages in all.
    const neighbours = wrapper.findAll('[data-testid="neighbours"] li')
    expect(neighbours).toHaveLength(3)
    expect(wrapper.get('[data-testid="search-consumption"]').text()).toContain('Ce que cette recherche a consommé')
    expect(wrapper.get('[data-testid="consumption-energy"]').text()).toMatch(/Wh/)
  })

  it('puts the pages of a PDF in a row, and says which pages each neighbour looks like', async () => {
    const { wrapper } = await searched(pdf(), 2)
    const pages = wrapper.findAll('[data-testid="graph"] [data-testid^="node-page-"]')
    expect(pages).toHaveLength(3)
    // The same height, from left to right.
    const at = pages.map((p) => /translate\(([\d.]+) ([\d.]+)\)/.exec(p.attributes('transform')!)!.slice(1).map(Number))
    expect(new Set(at.map(([, y]) => y)).size).toBe(1)
    expect(at.map(([x]) => x)).toEqual([...at.map(([x]) => x)].sort((a, b) => a - b))
    expect(pages.map((p) => p.attributes('aria-label'))).toEqual([
      'Page du document envoyé : Page 1',
      'Page du document envoyé : Page 2',
      'Page du document envoyé : Page 3',
    ])
    expect(wrapper.get('[data-testid="meta"]').text()).toContain('3 pages')
    expect(wrapper.findAll('[data-testid="neighbour-pages"]').length).toBeGreaterThan(0)
    expect(wrapper.get('[data-testid="neighbour-pages"]').text()).toMatch(/^· pages? \d/)
  })

  it('does not say which page when the document has only one', async () => {
    const { wrapper } = await searched(png())
    expect(wrapper.find('[data-testid="neighbour-pages"]').exists()).toBe(false)
  })

  it('chooses a neighbour, and links to its model', async () => {
    const { wrapper, router } = await searched(png())
    const first = wrapper.get('[data-testid="neighbours"] li button')
    await first.trigger('click')
    expect(first.attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="selected"]').text()).toContain('ressemble à')
    await wrapper.get('[data-testid="open-model"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('catalogue-detail'))
    await first.trigger('click').catch(() => undefined)
  })

  it('chooses a neighbour from the graph with the keyboard', async () => {
    const { wrapper } = await searched(png())
    const node = wrapper.get('[data-testid="graph"] [data-testid^="node-"][role="button"]')
    await node.trigger('keydown', { key: 'Enter' })
    expect(node.attributes('aria-pressed')).toBe('true')
    await node.trigger('keydown', { key: 'Enter' })
    expect(wrapper.find('[data-testid="selected"]').exists()).toBe(false)
  })

  it('is running while the worker computes, then shows the result and what it consumed', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const { wrapper } = await searched(png('slow.png'))
    expect(wrapper.get('[data-testid="running"]').text()).toContain('Recherche des documents proches')
    expect(wrapper.find('[data-testid="graph"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="search-consumption"]').exists()).toBe(false)
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()
    expect(wrapper.find('[data-testid="running"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="graph"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="search-consumption"]').exists()).toBe(true)
  })

  it('says it failed, with nothing to show', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const { wrapper } = await searched(png('broken.png'))
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()
    expect(wrapper.get('[data-testid="failed"]').text()).toContain('a échoué')
    expect(wrapper.find('[data-testid="graph"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="search-consumption"]').exists()).toBe(false)
  })

  it('says when no model looks like the document', async () => {
    const { id } = await useSearches().start(png(), 3, ['ghost'])
    resetSearches()
    const { wrapper } = await mountAt(`/recherche/${id}`)
    await vi.waitFor(() => expect(wrapper.find('[data-testid="none"]').exists()).toBe(true))
  })

  it('says a search that is not there, or is not the person’s, is not there', async () => {
    const { wrapper } = await mountAt('/recherche/nope')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="fault"]').exists()).toBe(true))
    expect(wrapper.get('[data-testid="fault"]').text()).toContain('n’existe pas')
  })

  it('goes back to the searches, and to a new one', async () => {
    const { wrapper, router } = await searched(png())
    await wrapper.get('[data-testid="again"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('search'))
  })

  it('counts in what the person consumed', async () => {
    await useSearches().start(png(), 3, null)
    await useSearches().start(png('deux.png'), 3, null)
    const { wrapper } = await mountAt('/parametres/consommation')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="consumption-searches"]').exists()).toBe(true))
    expect(wrapper.get('[data-testid="consumption-searches-count"]').text()).toContain('2 recherches, dont 2 mesurées')
    expect(wrapper.get('[data-testid="my-searches-consumption"]').text()).toContain('Toutes mes recherches')
    expect(wrapper.find('[data-testid="consumption-none"]').exists()).toBe(false)
  })
})
