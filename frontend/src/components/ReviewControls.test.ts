import VueDsfr from '@gouvminint/vue-dsfr'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Review } from '../data/mock'
import ReviewControls from './ReviewControls.vue'

const models = [
  { id: 't1', name: 'Logo Marianne' },
  { id: 't6', name: 'Filigrane « Copie »' },
]
const modelName = (id: string) => models.find((m) => m.id === id)?.name ?? id

const mountControls = (review: Review) => mount(ReviewControls, { props: { review, models, modelName }, global: { plugins: [VueDsfr] } })
const state = (w: ReturnType<typeof mount>) => w.get('[data-testid="review-state"]').text()

describe('ReviewControls', () => {
  it('says a prediction is still to look at, and has nothing to take back', () => {
    const wrapper = mountControls({ status: 'pending' })
    expect(state(wrapper)).toBe('À vérifier')
    expect(wrapper.find('[data-testid="review-reset"]').exists()).toBe(false)
  })

  it('says what was decided', () => {
    expect(state(mountControls({ status: 'validated' }))).toBe('Prédiction validée')
    expect(state(mountControls({ status: 'invalidated' }))).toBe('Prédiction invalidée')
    expect(state(mountControls({ status: 'annotated', templateId: 't6' }))).toBe('Annotée : Filigrane « Copie »')
  })

  it('validates or invalidates with a button', async () => {
    const wrapper = mountControls({ status: 'pending' })
    await wrapper.get('[data-testid="review-validate"]').trigger('click')
    await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
    expect(wrapper.emitted('review')).toEqual([[{ status: 'validated' }], [{ status: 'invalidated' }]])
  })

  it('marks which of the two was chosen, for a screen reader and by its look', () => {
    const validated = mountControls({ status: 'validated' })
    expect(validated.get('[data-testid="review-validate"]').attributes('aria-pressed')).toBe('true')
    expect(validated.get('[data-testid="review-validate"]').classes()).not.toContain('fr-btn--secondary')
    expect(validated.get('[data-testid="review-invalidate"]').attributes('aria-pressed')).toBe('false')
    expect(validated.get('[data-testid="review-invalidate"]').classes()).toContain('fr-btn--secondary')
  })

  it('offers only the models of the analysis to annotate with', () => {
    const options = mountControls({ status: 'pending' }).findAll('[data-testid="review-annotate"] option')
    expect(options.map((o) => o.text())).toEqual(['Annoter avec…', 'Logo Marianne', 'Filigrane « Copie »'])
    expect(options[0].attributes('disabled')).toBeDefined() // the title of the list is not a choice
  })

  it('annotates as soon as a model is picked', async () => {
    const wrapper = mountControls({ status: 'pending' })
    await wrapper.get('[data-testid="review-annotate"]').setValue('t6')
    expect(wrapper.emitted('review')).toEqual([[{ status: 'annotated', templateId: 't6' }]])
  })

  it('shows the model an annotation was made with', () => {
    const select = mountControls({ status: 'annotated', templateId: 't6' }).get('[data-testid="review-annotate"]').element as HTMLSelectElement
    expect(select.value).toBe('t6')
    const none = mountControls({ status: 'validated' }).get('[data-testid="review-annotate"]').element as HTMLSelectElement
    expect(none.value).toBe('')
  })

  it('takes a decision back', async () => {
    const wrapper = mountControls({ status: 'invalidated' })
    await wrapper.get('[data-testid="review-reset"]').trigger('click')
    expect(wrapper.emitted('review')).toEqual([[{ status: 'pending' }]])
  })

  it('names the list of models for a screen reader', () => {
    const wrapper = mountControls({ status: 'pending' })
    const id = wrapper.get('[data-testid="review-annotate"]').attributes('id')
    expect(wrapper.get(`label[for="${id}"]`).text()).toBe('Annoter avec un modèle de l’analyse')
  })

  describe('for the page of a document', () => {
    const pages = [
      { id: 'f', name: 'Formulaire X · page 1', page: 1 },
      { id: 'f', name: 'Formulaire X · Pièces', page: 2 },
      { id: 't1', name: 'Logo Marianne' },
    ]
    const label = (id: string, page?: number | null) => pages.find((m) => m.id === id && m.page === (page ?? undefined))?.name ?? id
    const mountPages = (review: Review) =>
      mount(ReviewControls, { props: { review, models: pages, modelName: label }, global: { plugins: [VueDsfr] } })

    it('offers the pages of the models, and the model when it has one page', () => {
      const options = mountPages({ status: 'pending' }).findAll('option')
      expect(options.map((o) => [o.text(), o.attributes('value')])).toEqual([
        ['Annoter avec…', ''],
        ['Formulaire X · page 1', 'f#1'],
        ['Formulaire X · Pièces', 'f#2'],
        ['Logo Marianne', 't1'],
      ])
    })

    it('annotates with a page of a model, or with a model alone', async () => {
      const wrapper = mountPages({ status: 'pending' })
      await wrapper.get('select').setValue('f#2')
      await wrapper.get('select').setValue('t1')
      expect(wrapper.emitted('review')).toEqual([
        [{ status: 'annotated', templateId: 'f', templatePage: 2 }],
        [{ status: 'annotated', templateId: 't1' }],
      ])
    })

    it('says which page it was annotated with, and shows it chosen', () => {
      const wrapper = mountPages({ status: 'annotated', templateId: 'f', templatePage: 2 })
      expect(state(wrapper)).toBe('Annotée : Formulaire X · Pièces')
      expect((wrapper.get('select').element as HTMLSelectElement).value).toBe('f#2')
    })
  })
})
