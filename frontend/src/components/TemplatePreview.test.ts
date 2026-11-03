import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { loadCatalogue, resetCatalogue, useCatalogue } from '../composables/useCatalogue'
import { loadEntityTypes } from '../composables/useEntityTypes'
import { useSession } from '../composables/useSession'
import TemplatePreview from './TemplatePreview.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/catalogue/:id', name: 'catalogue-detail', component: { template: '<i/>' } }],
})

const mountPreview = (template: ReturnType<ReturnType<typeof useCatalogue>['find']>) =>
  mount(TemplatePreview, { props: { template: template ?? null }, global: { plugins: [VueDsfr, router] }, attachTo: document.body })

describe('TemplatePreview', () => {
  beforeEach(async () => {
    resetCatalogue()
    useSession().setUser('dana')
    await loadEntityTypes()
    await loadCatalogue()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  const dialog = (w: ReturnType<typeof mount>) => w.get('dialog').element as HTMLDialogElement

  it('is closed while there is no model, and shows nothing', async () => {
    const wrapper = mountPreview(null)
    await flushPromises()
    expect(dialog(wrapper).open).toBe(false)
    expect(wrapper.find('[data-testid="preview"]').exists()).toBe(false)
  })

  it('opens on a model, with its name, owner, categories and description', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    expect(dialog(wrapper).open).toBe(true) // the dialog's own method is missing in jsdom: it is simply shown
    expect(wrapper.get('h2').text()).toBe('Logo Marianne')
    expect(wrapper.text()).toContain('alice.martin')
    expect(wrapper.findAll('.fr-tag').slice(0, 2).map((t) => t.text())).toEqual(['Identité', 'Officiel'])
    expect(wrapper.get('[data-testid="preview-description"]').text()).toBe('Bloc-marque de la République française.')
  })

  it('uses the browser\'s modal dialog when there is one, and closes it when the model goes', async () => {
    const showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute('open', '')
    })
    const close = vi.fn(function (this: HTMLDialogElement) {
      this.removeAttribute('open')
    })
    HTMLDialogElement.prototype.showModal = showModal
    HTMLDialogElement.prototype.close = close
    try {
      const wrapper = mountPreview(useCatalogue().find('t1'))
      await flushPromises()
      expect(showModal).toHaveBeenCalledTimes(1)
      await wrapper.setProps({ template: null })
      await flushPromises()
      expect(close).toHaveBeenCalledTimes(1)
      expect(dialog(wrapper).open).toBe(false)
    } finally {
      // @ts-expect-error: put back what jsdom has, which is nothing
      delete HTMLDialogElement.prototype.showModal
      // @ts-expect-error: ditto
      delete HTMLDialogElement.prototype.close
    }
  })

  it('shows the document with the zones, and the entities one at a time', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    expect(wrapper.find('.doc-viewer').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="entity-zone"]')).toHaveLength(1)
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 2')
    expect(wrapper.get('[data-testid="entity"]').text()).toContain('Emblème')
    expect(wrapper.find('.doc-viewer__polygon--highlight').exists()).toBe(true) // the entity on show
    await wrapper.get('button[title="Entité suivante"]').trigger('click')
    expect(wrapper.get('[data-testid="entity"]').text()).toContain('Devise')
    expect(wrapper.find('.doc-viewer__polygon--highlight').exists()).toBe(false) // that one has no zone
  })

  it('has no document area for a model without a document', async () => {
    const wrapper = mountPreview(useCatalogue().find('t3'))
    await flushPromises()
    expect(wrapper.find('.preview__document').exists()).toBe(false)
    expect(wrapper.find('.preview__body--with-document').exists()).toBe(false)
    expect(wrapper.text()).toContain('Aucune entité définie pour ce modèle.')
  })

  it('goes back to the first entity when it shows another model', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    await wrapper.get('button[title="Entité suivante"]').trigger('click')
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('2 / 2')
    await wrapper.setProps({ template: useCatalogue().find('t2') })
    await flushPromises()
    expect(wrapper.get('h2').text()).toBe('Tampon « Reçu »')
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 1')
  })

  it('points to the page of the model', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    expect(wrapper.get('footer a').attributes('href')).toBe('/catalogue/t1')
    expect(wrapper.get('footer a').text()).toBe('Ouvrir la page du modèle')
  })

  it('says it is closed: with its button, with Escape (the dialog\'s own close), and with a click outside', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    await wrapper.get('[data-testid="preview-close"]').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
    dialog(wrapper).dispatchEvent(new Event('close'))
    expect(wrapper.emitted('close')).toHaveLength(2)
    await wrapper.get('dialog').trigger('click') // on the dimmed area: the target is the dialog itself
    expect(wrapper.emitted('close')).toHaveLength(3)
    await wrapper.get('h2').trigger('click') // inside: not a click outside
    expect(wrapper.emitted('close')).toHaveLength(3)
  })

  it('lets an entity be starred from there', async () => {
    const wrapper = mountPreview(useCatalogue().find('t1'))
    await flushPromises()
    const star = () => wrapper.get('[data-testid="entity-star"]')
    expect(star().text()).toContain('2')
    await star().trigger('click')
    await flushPromises()
    await wrapper.setProps({ template: useCatalogue().find('t1') }) // the page hands the new one over
    expect(star().text()).toContain('3')
    expect(useCatalogue().find('t1')!.entities[0].stars).toContain('dana')
  })
})
