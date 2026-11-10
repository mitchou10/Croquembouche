import VueDsfr from '@gouvminint/vue-dsfr'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { TemplateEntity } from '../data/mock'
import EntitiesEditor from './EntitiesEditor.vue'

const entity = (id: string, name: string): TemplateEntity => ({ id, name, definition: '', type: 'text', examples: [], tags: [], zones: [], stars: [] })

describe('EntitiesEditor', () => {
  it('shows the entity the parent brings on show, as when a zone is clicked on the document', async () => {
    const entities = [entity('a', 'Date'), entity('b', 'Montant')]
    const wrapper = mount(EntitiesEditor, {
      props: { modelValue: entities, document: null, currentId: 'a' },
      global: { plugins: [VueDsfr] },
    })
    const name = () => {
      const label = wrapper.findAll('label').find((l) => l.text().startsWith('Nom'))!
      return (wrapper.get(`#${label.attributes('for')}`).element as HTMLInputElement).value
    }
    expect(name()).toBe('Date')
    await wrapper.setProps({ currentId: 'b' })
    expect(name()).toBe('Montant')
  })

  const square = (x: number) => ({ page: 1, points: [{ x, y: 0.1 }, { x: x + 0.2, y: 0.1 }, { x: x + 0.2, y: 0.3 }] })
  const doc = { name: 'a.png', type: 'image/png', url: 'blob:a' }

  function zoned(zones: number) {
    const entities = [{ ...entity('a', 'Numéro'), zones: Array.from({ length: zones }, (_, i) => square(0.1 * (i + 1))) }]
    const wrapper = mount(EntitiesEditor, { props: { modelValue: entities, document: doc }, global: { plugins: [VueDsfr] } })
    return { wrapper, entities }
  }

  it('lists the zones of an entity that has several, and edits the one chosen', async () => {
    const { wrapper } = zoned(3)
    const chips = wrapper.findAll('[data-testid="zone-chip"]')
    expect(chips.map((c) => c.text())).toEqual(['Zone 1', 'Zone 2', 'Zone 3'])
    await chips[1].trigger('click')
    expect(wrapper.emitted('update:currentZone')!.at(-1)).toEqual([1])
  })

  it('adds a zone after the others, and draws one again in place', async () => {
    const { wrapper } = zoned(2)
    await wrapper.get('[data-testid="add-zone"]').trigger('click')
    expect(wrapper.emitted('update:drawingZone')!.at(-1)).toEqual([2]) // past the last: a new one
    expect(wrapper.emitted('update:drawingId')!.at(-1)).toEqual(['a'])
  })

  it('removes the zone on show, and no more can be added at ten', async () => {
    const { wrapper, entities } = zoned(3)
    await wrapper.get('[data-testid="delete-zone"]').trigger('click')
    expect(entities[0].zones).toHaveLength(2)
    const full = zoned(10)
    expect(full.wrapper.find('[data-testid="add-zone"]').exists()).toBe(false)
  })

  it('wants a zone drawn for an entity that is found by zone', async () => {
    const { wrapper, entities } = zoned(1)
    await wrapper.get('[data-testid="delete-zone"]').trigger('click')
    expect(entities[0].zones).toEqual([])
    expect((wrapper.vm as unknown as { validate: () => boolean }).validate()).toBe(false)
  })
})
