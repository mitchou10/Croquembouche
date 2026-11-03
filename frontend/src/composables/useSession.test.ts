import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const respond = (body: unknown, ok = true) => vi.fn().mockResolvedValue({ ok, json: async () => body })

describe('useSession', () => {
  let assign: ReturnType<typeof vi.fn>

  // Fresh module each time: the session is a singleton that remembers having asked the backend.
  const fresh = async () => (await import('./useSession')).useSession()

  beforeEach(() => {
    vi.resetModules()
    assign = vi.fn()
    vi.stubGlobal('location', { assign })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('knows who is signed in from the backend, with the name when there is one', async () => {
    const fetch = respond({ user_id: 'u1', email: 'ada@example.org', first_name: 'Ada', last_name: 'L', is_admin: true })
    vi.stubGlobal('fetch', fetch)
    const session = await fresh()
    await session.load()
    expect(fetch).toHaveBeenCalledWith('/api/auth/me', { credentials: 'same-origin' })
    expect(session.userId.value).toBe('u1') // the account
    expect(session.displayName.value).toBe('Ada L')
    expect(session.email.value).toBe('ada@example.org')
    expect(session.isAdmin.value).toBe(true)
    expect(session.isAuthenticated.value).toBe(true)
  })

  it('falls back on the e-mail, then on the identifier, for the name', async () => {
    vi.stubGlobal('fetch', respond({ user_id: 'u1', email: 'ada@example.org', first_name: '', last_name: '', is_admin: false }))
    const session = await fresh()
    await session.load()
    expect(session.userId.value).toBe('u1')
    expect(session.displayName.value).toBe('ada@example.org')
    expect(session.isAdmin.value).toBe(false)
  })

  it('asks the backend once', async () => {
    const fetch = respond({ user_id: 'u1', email: '', first_name: '', last_name: '', is_admin: false })
    vi.stubGlobal('fetch', fetch)
    const session = await fresh()
    await Promise.all([session.load(), session.load()])
    await session.load()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('has nobody signed in without a session, or when the backend cannot be reached', async () => {
    vi.stubGlobal('fetch', respond({}, false))
    let session = await fresh()
    await session.load()
    expect(session.isAuthenticated.value).toBe(false)

    vi.resetModules()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    session = await fresh()
    await session.load()
    expect(session.isAuthenticated.value).toBe(false)
  })

  it('sends the browser to the backend to sign in, keeping to in-app paths', async () => {
    const session = await fresh()
    session.login('/analyses?x=1')
    expect(assign).toHaveBeenLastCalledWith('/api/auth/login?redirect=%2Fanalyses%3Fx%3D1')
    session.login('//evil.example')
    expect(assign).toHaveBeenLastCalledWith('/api/auth/login?redirect=%2Fcatalogue')
    session.login()
    expect(assign).toHaveBeenLastCalledWith('/api/auth/login?redirect=%2Fcatalogue')
  })

  it('signs out through the address the backend gives, and forgets the user', async () => {
    vi.stubGlobal('fetch', respond({ redirectUrl: 'http://keycloak/logout' }))
    const session = await fresh()
    session.setUser('alice', { isAdmin: true })
    await session.logout()
    expect(fetch).toHaveBeenCalledWith('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
    expect(session.userId.value).toBeNull()
    expect(session.isAdmin.value).toBe(false)
    expect(assign).toHaveBeenCalledWith('http://keycloak/logout')
  })

  it('goes home when the backend cannot end the session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const session = await fresh()
    session.setUser('alice')
    await session.logout()
    expect(session.isAuthenticated.value).toBe(false)
    expect(assign).toHaveBeenCalledWith('/')
  })
})
