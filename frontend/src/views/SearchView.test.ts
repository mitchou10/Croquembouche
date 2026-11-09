import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../App.vue'
import { resetCatalogue, useCatalogue } from '../composables/useCatalogue'
import { resetAnalyses } from '../composables/useAnalyses'
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

type Page = Awaited<ReturnType<typeof mountAt>>

async function send(page: Page, file: File) {
  const input = page.wrapper.get('[data-testid="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

const png = (name = 'facture.png') => new File([new Uint8Array(10)], name, { type: 'image/png' })
const pdf = (name = 'dossier.pdf') => new File([new Uint8Array(10)], name, { type: 'application/pdf' })
const landsOn = (page: Page, name: string) => vi.waitFor(() => expect(page.router.currentRoute.value.name).toBe(name))

/** Models that have a document, so that there is something to look like. */
async function makeModels() {
  const { create } = useCatalogue()
  const made = []
  for (const [name, type] of [['Facture', 'image/png'], ['Contrat', 'application/pdf'], ['Attestation', 'image/png']] as const) {
    const document = await uploadDocument(new File(['x'], `${name}.x`, { type }))
    made.push(await create({ name, description: '', categories: [], entities: [], pages: [] }, document))
  }
  return made
}

describe('the search page', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    URL.createObjectURL = vi.fn(() => 'blob:test')
    resetCatalogue()
    resetAnalyses()
    resetSearches()
    useSession().setUser('alice')
  })

  it('asks for a document, and says there is no search yet', async () => {
    const page = await mountAt('/recherche')
    expect(page.wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
    expect(page.wrapper.get('[data-testid="history-empty"]').text()).toContain('pas encore fait de recherche')
  })

  it('sends the document, and opens the search, which is kept', async () => {
    await makeModels()
    const page = await mountAt('/recherche')
    await send(page, png())
    await landsOn(page, 'search-detail')
    await flushPromises()
    expect(page.wrapper.get('[data-testid="title"]').text()).toBe('facture.png')
    expect(page.wrapper.get('[data-testid="graph"]').exists()).toBe(true)
    expect(useSearches().searches.value).toHaveLength(1)
  })

  it('refuses what is not an image or a PDF, and what is too big, without sending it', async () => {
    const page = await mountAt('/recherche')
    await send(page, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    expect(page.wrapper.get('[data-testid="fault"]').text()).toContain('Seuls les images')
    await send(page, new File([new Uint8Array(21 * 1024 * 1024)], 'gros.png', { type: 'image/png' }))
    expect(page.wrapper.get('[data-testid="fault"]').text()).toContain('trop lourd')
    expect(useSearches().searches.value).toHaveLength(0)
    expect(page.router.currentRoute.value.name).toBe('search')
  })

  it('looks in every model by default, and in the ones picked when asked', async () => {
    const [facture] = await makeModels()
    const page = await mountAt('/recherche')
    expect((page.wrapper.get('[data-testid="scope-all"]').element as HTMLInputElement).checked).toBe(true)
    expect(page.wrapper.find('[data-testid="scope-picker"]').exists()).toBe(false)

    await page.wrapper.get('[data-testid="scope-some"]').trigger('change')
    expect(page.wrapper.get('[data-testid="scope-count"]').text()).toBe('Aucun modèle choisi')
    await send(page, png()) // nothing picked: it cannot look nowhere
    expect(page.wrapper.get('[data-testid="fault"]').text()).toContain('au moins un modèle')

    await page.wrapper.get(`[data-testid="scope-model-${facture.id}"]`).trigger('change')
    expect(page.wrapper.get('[data-testid="scope-count"]').text()).toBe('1 modèle choisi')
    await send(page, png('scan.png'))
    await landsOn(page, 'search-detail')
    expect(useSearches().searches.value[0].templateIds).toEqual([facture.id])
  })

  it('keeps what was picked when it goes back to every model', async () => {
    const [facture] = await makeModels()
    const page = await mountAt('/recherche')
    await page.wrapper.get('[data-testid="scope-some"]').trigger('change')
    await page.wrapper.get(`[data-testid="scope-model-${facture.id}"]`).trigger('change')
    await page.wrapper.get('[data-testid="scope-all"]').trigger('change')
    await page.wrapper.get('[data-testid="scope-some"]').trigger('change')
    expect(page.wrapper.get('[data-testid="scope-count"]').text()).toBe('1 modèle choisi')
  })

  it('does not offer a model with no document to look like', async () => {
    await makeModels()
    await useCatalogue().create({ name: 'Sans exemple', description: '', categories: [], entities: [], pages: [] })
    const page = await mountAt('/recherche')
    await page.wrapper.get('[data-testid="scope-some"]').trigger('change')
    const labels = page.wrapper.findAll('[data-testid="scope-picker"] label').map((l) => l.text())
    expect(labels).toEqual(expect.arrayContaining(['Facture', 'Contrat', 'Attestation']))
    expect(labels).not.toContain('Sans exemple')
  })

  it('asks for as many neighbours as wanted, between the limits', async () => {
    await makeModels()
    const page = await mountAt('/recherche')
    const k = page.wrapper.get('[data-testid="k"]')
    ;(k.element as HTMLInputElement).value = '99'
    await k.trigger('change')
    expect((k.element as HTMLInputElement).value).toBe('12')
    ;(k.element as HTMLInputElement).value = '2'
    await k.trigger('change')
    await send(page, png())
    await landsOn(page, 'search-detail')
    expect(useSearches().searches.value[0].k).toBe(2)
  })

  it('lists the searches made, each with what it consumed, and opens one again', async () => {
    await makeModels()
    await useSearches().start(png('ancienne.png'), 3, null)
    resetSearches()
    const page = await mountAt('/recherche')
    const rows = page.wrapper.findAll('[data-testid="history"] li')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('ancienne.png')
    expect(rows[0].text()).toContain('1 page')
    expect(rows[0].text()).toContain('tous les modèles')
    expect(rows[0].get('[data-testid="history-consumption"]').text()).toMatch(/Wh/)
    await rows[0].get('a').trigger('click')
    await landsOn(page, 'search-detail')
    await flushPromises()
    expect(page.wrapper.get('[data-testid="title"]').text()).toBe('ancienne.png')
  })

  it('deletes a search once it is sure', async () => {
    await useSearches().start(png('ancienne.png'), 3, null)
    resetSearches()
    const page = await mountAt('/recherche')
    await page.wrapper.get('[data-testid="history"] [data-testid="delete"]').trigger('click')
    expect(page.wrapper.findAll('[data-testid="history"] li')).toHaveLength(1) // asked, not done yet
    await page.wrapper.get('[data-testid="confirm-yes"]').trigger('click')
    expect(page.wrapper.find('[data-testid="history"]').exists()).toBe(false)
    expect(page.wrapper.get('[data-testid="history-empty"]').exists()).toBe(true)
  })

  it('says the searches could not be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn((path: string) => (path === '/api/searches' ? Promise.reject(new Error('down')) : Promise.resolve(new Response('[]')))))
    const page = await mountAt('/recherche')
    expect(page.wrapper.get('[data-testid="history-failed"]').exists()).toBe(true)
  })

  it('is in the sidebar', async () => {
    const page = await mountAt('/recherche')
    expect(page.wrapper.findAll('.app-sidebar__link').map((l) => l.text())).toContain('Recherche')
  })
})
