import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { frontendVersion, resetVersions } from '../composables/useVersions'
import { routes } from '../router'
import AppSidebar from './AppSidebar.vue'

async function mountSidebar() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push('/catalogue')
  const wrapper = mount(AppSidebar, { global: { plugins: [VueDsfr, router] } })
  await flushPromises()
  return wrapper
}

const answering = (answer: () => Response | Promise<Response>) => vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(answer())))
const text = (wrapper: Awaited<ReturnType<typeof mountSidebar>>, id: string) => wrapper.get(`[data-testid="${id}"]`).text()

describe('the versions in the sidebar', () => {
  beforeEach(() => resetVersions())

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
