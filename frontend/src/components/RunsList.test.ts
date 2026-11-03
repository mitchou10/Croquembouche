import VueDsfr from '@gouvminint/vue-dsfr'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { AnalysisRun } from '../data/mock'
import RunsList from './RunsList.vue'

const runs = (n: number): AnalysisRun[] =>
  Array.from({ length: n }, (_, i) => ({
    id: `r${i}`,
    userId: `user${i}`,
    date: `2026-10-${String(30 - i).padStart(2, '0')}`,
    status: i % 3 === 0 ? 'done' : i % 3 === 1 ? 'running' : 'failed',
    matches: i,
  }))

const mountList = (n: number, props: Record<string, unknown> = {}) =>
  mount(RunsList, { props: { runs: runs(n), canSee: () => false, ...props }, global: { plugins: [VueDsfr] } })

describe('RunsList', () => {
  it('says so when there is no use yet', () => {
    expect(mountList(0).text()).toContain('Cette analyse n’a pas encore été utilisée.')
  })

  it('shows a use with its date, who ran it, how it went and what it found', () => {
    const row = mountList(2).get('[data-testid="run"]')
    expect(row.text()).toContain('2026-10-30')
    expect(row.text()).toContain('user0')
    expect(row.text()).toContain('Terminée')
    expect(row.text()).toContain('0 correspondance')
  })

  it('says « correspondances » from two on', () => {
    const rows = mountList(3).findAll('[data-testid="run"]')
    expect(rows[1].text()).toContain('1 correspondance')
    expect(rows[1].text()).not.toContain('correspondances')
    expect(rows[2].text()).toContain('2 correspondances')
  })

  it('has no pager for four uses or fewer', () => {
    const wrapper = mountList(4)
    expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(4)
    expect(wrapper.find('[data-testid="pager-count"]').exists()).toBe(false)
  })

  it('shows four at a time, and pages through the rest', async () => {
    const wrapper = mountList(9)
    expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(4)
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 3')
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(wrapper.findAll('[data-testid="run"]')[0].text()).toContain('user4')
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(1)
    expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('3 / 3')
  })

  describe('the result of a use', () => {
    const withResult = (n: number): AnalysisRun[] => runs(n).map((r) => ({ ...r, detections: [] }))
    const mountResults = (list: AnalysisRun[], canSee: (r: AnalysisRun) => boolean, selectedId?: string) =>
      mount(RunsList, { props: { runs: list, canSee, selectedId }, global: { plugins: [VueDsfr] } })

    it('has a button to see it for the person who ran the use', () => {
      const wrapper = mountResults(withResult(2), (r) => r.id === 'r0')
      const rows = wrapper.findAll('[data-testid="run"]')
      expect(rows[0].get('[data-testid="run-open"]').text()).toBe('Voir le résultat du 2026-10-30')
      expect(rows[0].find('[data-testid="run-private"]').exists()).toBe(false)
    })

    it('says it is private for anyone else', () => {
      const wrapper = mountResults(withResult(2), (r) => r.id === 'r0')
      const other = wrapper.findAll('[data-testid="run"]')[1]
      expect(other.find('[data-testid="run-open"]').exists()).toBe(false)
      expect(other.get('[data-testid="run-private"]').text()).toBe('Résultat privé')
      expect(other.get('[data-testid="run-private"]').attributes('title')).toContain('Seule la personne qui a lancé l’analyse')
    })

    it('has neither for a use that stored no result', () => {
      const wrapper = mountResults(runs(2), () => true)
      expect(wrapper.find('[data-testid="run-open"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="run-private"]').exists()).toBe(false)
    })

    it('says which use is open, for a screen reader and by its look', () => {
      const wrapper = mountResults(withResult(2), () => true, 'r1')
      const buttons = wrapper.findAll('[data-testid="run-open"]')
      expect(buttons.map((b) => b.attributes('aria-pressed'))).toEqual(['false', 'true'])
      expect(wrapper.findAll('[data-testid="run"]').map((r) => r.classes().includes('runs__row--selected'))).toEqual([false, true])
    })

    it('says which use is to be opened', async () => {
      const wrapper = mountResults(withResult(3), () => true)
      await wrapper.findAll('[data-testid="run-open"]')[2].trigger('click')
      expect(wrapper.emitted('open')).toEqual([['r2']])
    })
  })
})
