import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { Detection } from '../composables/useAnalyses'
import DetectionCard from './DetectionCard.vue'

const names: Record<string, string> = { t1: 'Logo Marianne', t2: 'Tampon', t3: 'Signature', t4: 'Code QR', t5: 'Paraphe' }
const nameOf = (id: string | null) => (id === null ? 'Autre, non reconnu' : names[id])
const zone = { page: 1, points: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }] }

const mountCard = (classifications: Detection['classifications'], position = 1) =>
  mount(DetectionCard, { props: { detection: { id: 'd1', zone, classifications }, position, nameOf }, global: { plugins: [VueDsfr] } })

describe('DetectionCard', () => {
  it('says which zone of its entity it was found from, when the entity has several', () => {
    const classifications = [{ templateId: 't1', confidence: 0.9 }, { templateId: null, confidence: 0.1 }]
    const card = (detection: object, zoneCount?: number) =>
      mount(DetectionCard, { props: { detection: { id: 'd1', zone, classifications, ...detection }, zoneCount, nameOf }, global: { plugins: [VueDsfr] } })

    expect(card({ zoneIndex: 1 }, 3).get('[data-testid="detection-zone"]').text()).toBe('zone 2 sur 3')
    expect(card({ zoneIndex: 0 }, 1).find('[data-testid="detection-zone"]').exists()).toBe(false)
    expect(card({}, 3).find('[data-testid="detection-zone"]').exists()).toBe(false)
  })

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

  describe('copying the text of the zone', () => {
    const withText = (text?: string) =>
      mount(DetectionCard, {
        props: { detection: { id: 'd1', zone, classifications: [{ templateId: 't1', confidence: 0.9 }], text }, position: 1, nameOf },
        global: { plugins: [VueDsfr] },
      })

    it('has the button, waiting, while the zone has not been read', () => {
      const wrapper = withText()
      expect(wrapper.get('[data-testid="detection-copy"]').attributes('disabled')).toBeDefined()
      expect(wrapper.find('[data-testid="detection-text-pending"]').exists()).toBe(true)
    })

    const read = (props: Record<string, unknown>) =>
      mount(DetectionCard, {
        props: { detection: { id: 'd1', zone, classifications: [{ templateId: 't1', confidence: 0.9 }] }, position: 1, nameOf, ...props },
        global: { plugins: [VueDsfr] },
      })

    it('says the text is being read, failed, or empty, according to the reading', () => {
      expect(read({ ocrStatus: 'running' }).get('[data-testid="detection-text-pending"]').text()).toContain('en cours')
      expect(read({ ocrStatus: 'failed' }).get('[data-testid="detection-text-pending"]').text()).toContain('échoué')
      expect(read({ ocrStatus: 'done' }).get('[data-testid="detection-text-pending"]').text()).toBe('Aucun texte lu dans cette zone.')
    })

    it('says when it was found in the text, by the definition of its entity', () => {
      expect(read({}).find('[data-testid="detection-in-text"]').exists()).toBe(false)
      const wrapper = mount(DetectionCard, {
        props: { detection: { id: 'd1', zone, classifications: [{ templateId: 't1', confidence: 0.9 }], foundInText: true, text: '2026-0042' }, position: 1, nameOf },
        global: { plugins: [VueDsfr] },
      })
      expect(wrapper.get('[data-testid="detection-in-text"]').text()).toContain('à partir de la définition')
      expect(wrapper.get('[data-testid="detection-text"]').text()).toBe('2026-0042')
    })

    it('has no text and no button for an image or a table', () => {
      for (const [entityType, noun] of [['image', 'une image'], ['table', 'un tableau']]) {
        const wrapper = read({ entityType, ocrStatus: 'done' })
        expect(wrapper.get('[data-testid="detection-no-text"]').text()).toBe(`Pas de texte à lire pour ${noun}.`)
        expect(wrapper.find('[data-testid="detection-copy"]').exists()).toBe(false)
      }
      expect(read({ entityType: 'date' }).find('[data-testid="detection-copy"]').exists()).toBe(true)
    })

    it('shows the text and copies it', async () => {
      const writeText = vi.fn().mockResolvedValue(undefined)
      vi.stubGlobal('navigator', { clipboard: { writeText } })
      const wrapper = withText('12/03/2026')
      expect(wrapper.get('[data-testid="detection-text"]').text()).toBe('12/03/2026')
      await wrapper.get('[data-testid="detection-copy"]').trigger('click')
      await flushPromises()
      expect(writeText).toHaveBeenCalledWith('12/03/2026')
      expect(wrapper.get('[data-testid="detection-copied"]').text()).toBe('Copié')
      vi.unstubAllGlobals()
    })

    it('says so when the copy is refused', async () => {
      vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
      const wrapper = withText('abc')
      await wrapper.get('[data-testid="detection-copy"]').trigger('click')
      await flushPromises()
      expect(wrapper.get('[data-testid="detection-copied"]').text()).toBe('Copie impossible')
      vi.unstubAllGlobals()
    })
  })
})
