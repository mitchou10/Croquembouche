import { describe, expect, it } from 'vitest'
import { ForbiddenError } from '../src/index.js'
import { FakeAPI } from './fake.js'

describe('users', () => {
  it('forgets what the token sent', async () => {
    const api = new FakeAPI()
    api.on('DELETE /api/users/me/data', { runs: 2, searches: 1, documents: 3 })

    expect(await api.client().users.purgeMyData()).toEqual({ runs: 2, searches: 1, documents: 3 })
  })

  it('leaves what another person sent to an administrator', async () => {
    const api = new FakeAPI()
    api.on('DELETE /api/users/bob/data', { detail: 'Seul un administrateur efface les envois d’une autre personne.' }, 403)

    await expect(api.client().users.purge('bob')).rejects.toBeInstanceOf(ForbiddenError)
  })
})
