import VueDsfr from '@gouvminint/vue-dsfr'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { TemplateEntity } from '../data/mock'
import EntitiesEditor from './EntitiesEditor.vue'

const entity = (id: string, name: string): TemplateEntity => ({ id, name, definition: '', type: 'text', examples: [], tags: [], stars: [] })

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
})
