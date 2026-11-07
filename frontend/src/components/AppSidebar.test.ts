import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { frontendVersion, resetVersions } from '../composables/useVersions'
import { routes } from '../router'
import AppSidebar from './AppSidebar.vue'

async function mountSidebar(opened = true) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push('/catalogue')
  const wrapper = mount(AppSidebar, { global: { plugins: [VueDsfr, router] }, attachTo: document.body })
  await flushPromises()
  if (opened) await wrapper.get('.app-sidebar__user').trigger('click')
  return Object.assign(wrapper, { router })
}

const answering = (answer: () => Response | Promise<Response>) => vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(answer())))
const text = (wrapper: Awaited<ReturnType<typeof mountSidebar>>, id: string) => wrapper.get(`[data-testid="${id}"]`).text()

describe('the menu of the account', () => {
  beforeEach(() => resetVersions())
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('is closed until the name is clicked, and says so to assistive technologies', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar(false)
    const name = wrapper.get('.app-sidebar__user')
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false)
    expect(name.attributes('aria-haspopup')).toBe('menu')
    expect(name.attributes('aria-expanded')).toBe('false')

    await name.trigger('click')
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(true)
    expect(name.attributes('aria-expanded')).toBe('true')
    await name.trigger('click') // the name opens it and closes it
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false)
  })

  it('has my consumption, my profile and signing out, then the versions at the bottom', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar()

    expect(wrapper.findAll('[role="menuitem"]').map((item) => item.text())).toEqual(['Ma consommation', 'Mon profil', 'Se déconnecter'])
    const menu = wrapper.get('[data-testid="account-menu"]').element
    expect(menu.lastElementChild).toBe(wrapper.get('[data-testid="app-versions"]').element)
  })

  it('goes to the page that is chosen, and closes', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar()

    await wrapper.get('[data-testid="menu-consumption"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.router.currentRoute.value.name).toBe('my-consumption'))
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false)
  })

  it('closes on Escape, the focus going back to the name', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar()

    await wrapper.get('[data-testid="menu-profile"]').trigger('keydown', { key: 'Escape' })

    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.get('.app-sidebar__user').element)
  })

  it('closes on a click elsewhere, and not on one inside', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar()

    wrapper.get('[data-testid="app-versions"]').element.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(true)

    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false)
  })
})

describe('the versions in the menu', () => {
  beforeEach(() => resetVersions())
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('says the version of the frontend, which is the one of package.json, and the one of the backend', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    const wrapper = await mountSidebar()

    expect(frontendVersion).toMatch(/^\d+\.\d+\.\d+/)
    expect(text(wrapper, 'app-version-frontend')).toBe(`v${frontendVersion}`)
    expect(text(wrapper, 'app-version-backend')).toBe(`v${frontendVersion}`)
    expect(wrapper.get('[data-testid="app-versions"]').classes()).not.toContain('app-sidebar__version--differ')
  })

  it('says so when the two are not the same version, the one that is not up to date being one of them', async () => {
    answering(() => Response.json({ version: '0.0.1' }))
    const wrapper = await mountSidebar()

    expect(text(wrapper, 'app-version-backend')).toBe('v0.0.1')
    const versions = wrapper.get('[data-testid="app-versions"]')
    expect(versions.classes()).toContain('app-sidebar__version--differ')
    expect(versions.attributes('title')).toContain('pas de la même version')
  })

  it('does not hide the frontend when the backend cannot be asked', async () => {
    answering(() => new Response('{}', { status: 500 }))
    const wrapper = await mountSidebar()

    expect(text(wrapper, 'app-version-frontend')).toBe(`v${frontendVersion}`)
    expect(text(wrapper, 'app-version-backend')).toBe('indisponible')
    expect(wrapper.get('[data-testid="app-versions"]').classes()).not.toContain('app-sidebar__version--differ')
  })

  it('asks the backend once, whatever the pages that show it', async () => {
    answering(() => Response.json({ version: frontendVersion }))
    await mountSidebar()
    await mountSidebar()

    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes('/api/version'))).toHaveLength(1)
  })
})
