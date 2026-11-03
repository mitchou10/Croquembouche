import { beforeEach, describe, expect, it } from 'vitest'
import { useSession } from './useSession'

describe('useSession', () => {
  beforeEach(() => {
    localStorage.clear()
    useSession().logout()
  })

  it('logs in with a trimmed identifier and remembers it', () => {
    const session = useSession()
    expect(session.login('  alice  ')).toBe(true)
    expect(session.userId.value).toBe('alice')
    expect(session.isAuthenticated.value).toBe(true)
    expect(localStorage.getItem('croquembouche.userId')).toBe('alice')
  })

  it('refuses a blank identifier', () => {
    const session = useSession()
    expect(session.login('   ')).toBe(false)
    expect(session.isAuthenticated.value).toBe(false)
  })

  it('logs out', () => {
    const session = useSession()
    session.login('alice')
    session.logout()
    expect(session.userId.value).toBeNull()
    expect(localStorage.getItem('croquembouche.userId')).toBeNull()
  })
})
