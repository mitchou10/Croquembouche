import VueDsfr from '@gouvminint/vue-dsfr'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Detection } from '../composables/useAnalyses'
import DetectionCard from './DetectionCard.vue'

const names: Record<string, string> = { t1: 'Logo Marianne', t2: 'Tampon', t3: 'Signature', t4: 'Code QR', t5: 'Paraphe' }
const nameOf = (id: string | null) => (id === null ? 'Autre, non reconnu' : names[id])
const zone = { page: 1, points: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }] }

const mountCard = (classifications: Detection['classifications'], position = 1) =>
  mount(DetectionCard, { props: { detection: { id: 'd1', zone, classifications }, position, nameOf }, global: { plugins: [VueDsfr] } })

describe('DetectionCard', () => {
  it('says which element it is, what it most likely is, and how sure', () => {
    const wrapper = mountCard([{ templateId: 't1', confidence: 0.92 }, { templateId: null, confidence: 0.08 }], 3)
    expect(wrapper.get('h3').text()).toBe('Élément 3')
    expect(wrapper.get('[data-testid="detection-best"]').text()).toBe('Logo Marianne')
    expect(wrapper.get('[data-testid="detection-confidence"]').text()).toBe('92 %')
  })

  it('lists every possible class with its confidence, the likeliest first', () => {
    const wrapper = mountCard([
      { templateId: 't1', confidence: 0.7 },
      { templateId: 't2', confidence: 0.2 },
      { templateId: null, confidence: 0.1 },
    ])
    const rows = wrapper.findAll('[data-testid="classification"]')
    expect(rows.map((r) => `${r.get('.classes__name').text()} ${r.get('.classes__percent').text()}`)).toEqual([
      'Logo Marianne 70 %',
      'Tampon 20 %',
      'Autre, non reconnu 10 %',
    ])
    expect(rows[0].classes()).toContain('classes__row--best')
    expect(rows[1].classes()).not.toContain('classes__row--best')
  })

  it('says in which version of a model a page was recognised, when it knows', () => {
    const wrapper = mountCard([{ templateId: 't1', templateVersion: '2.0.1', confidence: 0.7 }, { templateId: null, confidence: 0.3 }])
    const rows = wrapper.findAll('[data-testid="classification"]')
    expect(rows[0].get('.classes__name').text()).toBe('Logo Marianne · v2.0.1')
    expect(rows[1].get('.classes__name').text()).toBe('Autre, non reconnu')
  })

  it('draws each confidence as a bar a screen reader can read as a meter', () => {
    const wrapper = mountCard([{ templateId: 't2', confidence: 0.64 }, { templateId: null, confidence: 0.36 }])
    const meter = wrapper.findAll('[role="meter"]')[0]
    expect(meter.attributes('aria-valuenow')).toBe('64')
    expect(meter.attributes('aria-valuemin')).toBe('0')
    expect(meter.attributes('aria-valuemax')).toBe('100')
    expect(meter.attributes('aria-label')).toBe('Tampon : 64 %')
    expect(meter.get('.classes__fill').attributes('style')).toContain('width: 64%')
  })

  it('shows « other » as a warning when it is the likeliest: no model was recognised', () => {
    const wrapper = mountCard([{ templateId: null, confidence: 0.7 }, { templateId: 't1', confidence: 0.3 }])
    expect(wrapper.get('[data-testid="detection-best"]').classes()).toContain('fr-badge--warning')
    const known = mountCard([{ templateId: 't1', confidence: 0.9 }, { templateId: null, confidence: 0.1 }])
    expect(known.get('[data-testid="detection-best"]').classes()).toContain('fr-badge--success')
  })

  it('shows the four likeliest, and says how many more there are', () => {
    const wrapper = mountCard([
      { templateId: 't1', confidence: 0.5 },
      { templateId: 't2', confidence: 0.2 },
      { templateId: 't3', confidence: 0.12 },
      { templateId: 't4', confidence: 0.08 },
      { templateId: 't5', confidence: 0.06 },
      { templateId: null, confidence: 0.04 },
    ])
    expect(wrapper.findAll('[data-testid="classification"]')).toHaveLength(4)
    expect(wrapper.get('[data-testid="classifications-hidden"]').text()).toBe('+ 2 autres classes encore moins probables')
  })

  it('says « une autre classe » in the singular, and nothing when all are shown', () => {
    const five = mountCard([
      { templateId: 't1', confidence: 0.5 },
      { templateId: 't2', confidence: 0.2 },
      { templateId: 't3', confidence: 0.15 },
      { templateId: 't4', confidence: 0.1 },
      { templateId: null, confidence: 0.05 },
    ])
    expect(five.get('[data-testid="classifications-hidden"]').text()).toBe('+ 1 autre classe encore moins probable')
    const two = mountCard([{ templateId: 't1', confidence: 0.9 }, { templateId: null, confidence: 0.1 }])
    expect(two.find('[data-testid="classifications-hidden"]').exists()).toBe(false)
  })

  it('rounds a confidence to the nearest percent', () => {
    const wrapper = mountCard([{ templateId: 't1', confidence: 0.876 }, { templateId: null, confidence: 0.124 }])
    expect(wrapper.get('[data-testid="detection-confidence"]').text()).toBe('88 %')
  })

  it('has room, under the classes, for what the caller puts there', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: { id: 'd1', zone, classifications: [{ templateId: 't1', confidence: 1 }] }, position: 1, nameOf },
      slots: { default: '<div class="review-here">Valider</div>' },
      global: { plugins: [VueDsfr] },
    })
    expect(wrapper.get('.review-here').text()).toBe('Valider')
  })
})
