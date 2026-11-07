import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { METRICS, ORDER } from '../composables/qualityHelp'
import QualityBlocks from './QualityBlocks.vue'
import QualityHelp from './QualityHelp.vue'

const quality = { reviewed: 10, pending: 3, correct: 8, wrong: 2, missed: 4, precision: 0.8, recall: 0.6667, f1: 0.7273, meanConfidenceCorrect: 0.9, meanConfidenceWrong: 0.6 }

describe('QualityHelp', () => {
  it('explains every figure, in order, and follows an example through', () => {
    const wrapper = mount(QualityHelp)

    expect(wrapper.get('summary').text()).toBe('Comment lire ces chiffres ?')
    for (const key of ORDER) {
      const term = wrapper.get(`[data-testid="help-${key}"]`)
      expect(term.text()).toContain(METRICS[key].term)
      expect(term.text()).toContain(METRICS[key].text)
    }
    expect(wrapper.findAll('[data-testid^="help-"]').filter((e) => e.attributes('data-testid') !== 'help-example').length).toBe(ORDER.length)
    expect(wrapper.get('[data-testid="help-example"]').text()).toContain('8 ÷ 10 = 80 %')
    expect(wrapper.get('[data-testid="help-example"]').text()).toContain('8 ÷ 12 = 67 %')
  })

  it('says that the figures come from what people decide, not from a known answer', () => {
    expect(mount(QualityHelp).text()).toContain('ce que vous décidez')
  })
})

describe('QualityBlocks explanations', () => {
  const blocks = () => mount(QualityBlocks, { props: { pages: { ...quality, exact: 0.5 }, elements: quality } })

  it('puts a way to understand beside each ratio, each count and the confidence', async () => {
    const wrapper = blocks()
    const labels = wrapper.findAll('button.info-tip__button').map((b) => b.attributes('aria-label'))
    // Pages: precision, recall, F1, exact page, four counts, confidence; elements: the same without the exact page.
    expect(labels.filter((l) => l === 'Comprendre : Précision')).toHaveLength(2)
    expect(labels.filter((l) => l === 'Comprendre : Page du modèle exacte')).toHaveLength(1)
    for (const key of ['correct', 'wrong', 'missed', 'pending', 'confidence'] as const) {
      expect(labels.filter((l) => l === `Comprendre : ${METRICS[key].term}`)).toHaveLength(2)
    }
  })

  it('opens the explanation of a figure, with its question and its few words', async () => {
    const wrapper = blocks()
    const pages = wrapper.get('[data-testid="quality-pages"]')

    await pages.findAll('button.info-tip__button')[1].trigger('click') // the recall
    expect(pages.get('[role="note"]').text()).toBe(`${METRICS.recall.question} ${METRICS.recall.text}`)
  })

  it('keeps the figures as they were', () => {
    const wrapper = blocks()
    expect(wrapper.get('[data-testid="quality-pages"] [data-testid="precision"]').text()).toBe('80 %')
    expect(wrapper.get('[data-testid="quality-pages"] [data-testid="exact"]').text()).toBe('50 %')
    expect(wrapper.get('[data-testid="quality-elements"] [data-testid="counts"]').text()).toMatch(/^8 justes/)
  })
})
