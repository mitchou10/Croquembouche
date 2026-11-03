import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TabList from './TabList.vue'

const tabs = [
  { id: 'a', label: 'Premier' },
  { id: 'b', label: 'Second (3)' },
]

describe('TabList', () => {
  const mountTabs = (selected = 'a') => {
    const wrapper = mount(TabList, {
      props: { tabs, label: 'Deux onglets', modelValue: selected, 'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }) },
    })
    return wrapper
  }

  it('shows the tabs, named as a group, with the selected one marked', () => {
    const wrapper = mountTabs('b')
    expect(wrapper.get('[role="tablist"]').attributes('aria-label')).toBe('Deux onglets')
    expect(wrapper.findAll('[role="tab"]').map((t) => t.text())).toEqual(['Premier', 'Second (3)'])
    expect(wrapper.findAll('[role="tab"]').map((t) => t.attributes('aria-selected'))).toEqual(['false', 'true'])
  })

  it('lets only the selected tab take the focus, as a tab list does', () => {
    const wrapper = mountTabs('a')
    expect(wrapper.findAll('[role="tab"]').map((t) => t.attributes('tabindex'))).toEqual(['0', '-1'])
  })

  it('selects a tab when it is clicked', async () => {
    const wrapper = mountTabs('a')
    await wrapper.findAll('[role="tab"]')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['b'])
    expect(wrapper.findAll('[role="tab"]').map((t) => t.attributes('aria-selected'))).toEqual(['false', 'true'])
  })

  it('gives each tab its own id', () => {
    const ids = mountTabs().findAll('[role="tab"]').map((t) => t.attributes('id'))
    expect(new Set(ids).size).toBe(2)
  })
})
