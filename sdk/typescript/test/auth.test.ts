import { describe, expect, it } from 'vitest'
import {
  AuthenticationError,
  Croquembouche,
  bearerToken,
  clientCredentials,
  keycloakTokenUrl,
  tokenExchange,
} from '../src/index.js'
import { URL, template } from './fake.js'

const TOKEN_URL = 'http://keycloak.test/realms/r/protocol/openid-connect/token'

/** Keycloak and the API behind one `fetch`, and what the API saw as `Authorization`. */
class Both {
  asked: Record<string, string>[] = []
  bearers: (string | null)[] = []
  now = 1_000_000
  expiresIn = 300
  keycloakStatus = 200
  revoked = new Set<string>()

  fetch = async (input: Request | string | URL, init?: RequestInit): Promise<Response> => {
    const request = new Request(input, init)
    if (request.url === TOKEN_URL) {
      this.asked.push(Object.fromEntries(new URLSearchParams(await request.text())))
      if (this.keycloakStatus >= 400) {
        return Response.json({ error: 'invalid_client', error_description: 'Bad secret' }, { status: this.keycloakStatus })
      }
      return Response.json({ access_token: `token-${this.asked.length}`, expires_in: this.expiresIn })
    }
    const bearer = request.headers.get('authorization')
    this.bearers.push(bearer)
    if (this.revoked.has(bearer?.replace('Bearer ', '') ?? '')) {
      return Response.json({ detail: 'Not authenticated' }, { status: 401 })
    }
    return Response.json([template()])
  }

  clock = () => this.now

  service(): Croquembouche {
    const auth = clientCredentials({
      tokenUrl: TOKEN_URL,
      clientId: 'mille-feuille',
      clientSecret: 'secret',
      fetch: this.fetch as typeof fetch,
      now: this.clock,
    })
    return new Croquembouche(URL, { auth, fetch: this.fetch as typeof fetch })
  }
}

describe('auth', () => {
  it('knows the token endpoint of a realm', () => {
    expect(keycloakTokenUrl('http://kc/', 'croquembouche')).toBe('http://kc/realms/croquembouche/protocol/openid-connect/token')
  })

  it('gives a service account a token and keeps it until it is about to run out', async () => {
    const both = new Both()
    const client = both.service()

    await client.templates.list()
    await client.templates.list()
    expect(both.bearers).toEqual(['Bearer token-1', 'Bearer token-1'])
    expect(both.asked).toEqual([{ grant_type: 'client_credentials', client_id: 'mille-feuille', client_secret: 'secret' }])

    both.now += 269_000 // 300 seconds, less the 30 it is replaced before
    await client.templates.list()
    expect(both.asked).toHaveLength(1)
    both.now += 2_000
    await client.templates.list()
    expect(both.bearers.at(-1)).toBe('Bearer token-2')
    expect(both.asked).toHaveLength(2)
  })

  it('asks Keycloak once for requests that need a token at the same time', async () => {
    const both = new Both()
    const client = both.service()

    await Promise.all([client.templates.list(), client.templates.list(), client.templates.list()])

    expect(both.asked).toHaveLength(1)
  })

  it('asks for a token again, once, when the one it had was revoked', async () => {
    const both = new Both()
    both.revoked.add('token-1')

    expect(await both.service().templates.list()).toHaveLength(1)

    expect(both.bearers).toEqual(['Bearer token-1', 'Bearer token-2'])
  })

  it('throws an authentication error with its reason when Keycloak refuses', async () => {
    const both = new Both()
    both.keycloakStatus = 401

    const error = await both.service().templates.list().catch((e) => e)

    expect(error).toBeInstanceOf(AuthenticationError)
    expect(error.detail).toBe('Bad secret')
    expect(both.bearers).toEqual([])
  })

  it('exchanges the token of a person, asking for theirs again at each renewal', async () => {
    const both = new Both()
    const people = ['julie-1', 'julie-2']
    const auth = tokenExchange({
      tokenUrl: TOKEN_URL,
      clientId: 'mille-feuille',
      clientSecret: 'secret',
      subjectToken: () => people.shift()!,
      fetch: both.fetch as typeof fetch,
      now: both.clock,
    })
    const client = new Croquembouche(URL, { auth, fetch: both.fetch as typeof fetch })

    await client.templates.list()
    both.now += 1_000_000
    await client.templates.list()

    expect(both.asked[0]).toEqual({
      grant_type: 'urn:ietf:params:oauth:grant-type:token-exchange',
      client_id: 'mille-feuille',
      client_secret: 'secret',
      subject_token: 'julie-1',
      subject_token_type: 'urn:ietf:params:oauth:token-type:access_token',
      requested_token_type: 'urn:ietf:params:oauth:token-type:access_token',
      audience: 'croquembouche-backend',
    })
    expect(both.asked[1]?.subject_token).toBe('julie-2')
  })

  it('sends a token the program has as it is, or as its function gives it', async () => {
    const both = new Both()
    await new Croquembouche(URL, { token: 'abc', fetch: both.fetch as typeof fetch }).templates.list()
    await new Croquembouche(URL, {
      auth: bearerToken(async () => 'from-a-function'),
      fetch: both.fetch as typeof fetch,
    }).templates.list()
    expect(both.bearers).toEqual(['Bearer abc', 'Bearer from-a-function'])
  })

  it('takes a service account as plain options, or refuses half of one', async () => {
    const both = new Both()
    await new Croquembouche(URL, {
      tokenUrl: TOKEN_URL,
      clientId: 'mille-feuille',
      clientSecret: 'secret',
      fetch: both.fetch as typeof fetch,
    }).templates.list()
    expect(both.bearers).toEqual(['Bearer token-1'])

    expect(() => new Croquembouche(URL, { clientId: 'mille-feuille' })).toThrow(/together/)
  })

  it('sends nothing when there is nothing to sign in with', async () => {
    const both = new Both()
    await new Croquembouche(URL, { fetch: both.fetch as typeof fetch }).templates.list()
    expect(both.bearers).toEqual([null])
  })
})
