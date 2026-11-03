import { beforeEach, describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'
import { useSession } from '../composables/useSession'
import { requireAuth } from './index'

const route = (name: string, requiresAuth = false, fullPath = `/${name}`) =>
  ({ name, fullPath, meta: { requiresAuth } }) as unknown as RouteLocationNormalized

describe('requireAuth', () => {
  beforeEach(() => useSession().setUser(null))

  it('lets anyone reach a public page', async () => {
    expect(await requireAuth(route('landing'))).toBe(true)
  })

  it('sends a visitor to the login page, remembering where they were going', async () => {
    expect(await requireAuth(route('catalogue', true, '/catalogue'))).toEqual({
      name: 'login',
      query: { redirect: '/catalogue' },
    })
  })

  it('keeps the administrator\'s pages for the administrator, and sends anyone else to the analyses', async () => {
    const adminPage = { name: 'overview', fullPath: '/vue-d-ensemble', meta: { requiresAuth: true, requiresAdmin: true } } as unknown as RouteLocationNormalized
    useSession().setUser('dana')
    expect(await requireAuth(adminPage)).toEqual({ name: 'analyses' })
    useSession().setUser('admin', { isAdmin: true })
    expect(await requireAuth(adminPage)).toBe(true)
    useSession().setUser(null)
    expect(await requireAuth(adminPage)).toEqual({ name: 'login', query: { redirect: '/vue-d-ensemble' } }) // not signed in: first the login
  })

  it('lets a signed-in user through, and skips the login page for them', async () => {
    useSession().setUser('alice')
    expect(await requireAuth(route('analyses', true))).toBe(true)
    expect(await requireAuth(route('login'))).toEqual({ name: 'catalogue' })
  })
})
