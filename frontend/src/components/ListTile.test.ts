import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import ListTile from './ListTile.vue'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/m/:id', name: 'm', component: { template: '<i/>' } }] })

describe('ListTile', () => {
  it('shows the title and the description', () => {
    const wrapper = mount(ListTile, { props: { title: 'Logo', description: 'Le logo de la République.' } })
    expect(wrapper.get('h2').text()).toBe('Logo')
    expect(wrapper.get('.tile__description').text()).toBe('Le logo de la République.')
  })

  it('is not a link without a destination, and does not look like one', () => {
    const wrapper = mount(ListTile, { props: { title: 'Logo', description: 'x' } })
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.classes()).not.toContain('tile--link')
  })

  it('has its title as the one link, over the whole card, when given a destination', () => {
    const wrapper = mount(ListTile, {
      props: { title: 'Logo', description: 'x', to: { name: 'm', params: { id: '1' } } },
      global: { plugins: [router] },
    })
    expect(wrapper.findAll('a')).toHaveLength(1)
    expect(wrapper.get('a').attributes('href')).toBe('/m/1')
    expect(wrapper.get('a').text()).toBe('Logo')
    expect(wrapper.classes()).toContain('tile--link')
  })

  it('has a tags line and a details line only for what it is given', () => {
    const bare = mount(ListTile, { props: { title: 'a', description: 'b' } })
    expect(bare.find('.tile__tags').exists()).toBe(false)
    const full = mount(ListTile, {
      props: { title: 'a', description: 'b' },
      slots: { tags: '<span class="t">Tampon</span>', foot: '<span class="f">Par alice</span>' },
    })
    expect(full.get('.tile__tags .t').text()).toBe('Tampon')
    expect(full.get('.tile__foot .f').text()).toBe('Par alice')
  })
})
