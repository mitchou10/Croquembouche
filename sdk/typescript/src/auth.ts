// Tokens: the SDK asks Keycloak for them when it has none, and again before the one it has runs out.
//
// Three ways to have one, all of them renewing themselves: a service account (`clientCredentials`), the token of a person
// exchanged for one meant for Croquembouche (`tokenExchange`), or a token the program already has (`bearerToken`).
import { AuthenticationError } from './errors.js'

/** How long before it runs out a token is replaced (seconds): a request made with it must not arrive too late. */
export const LEEWAY = 30
const TOKEN_EXCHANGE = 'urn:ietf:params:oauth:grant-type:token-exchange'
const ACCESS_TOKEN = 'urn:ietf:params:oauth:token-type:access_token'

type Maybe<T> = T | Promise<T>
export type TokenProvider = () => Maybe<string>

/** Where the SDK gets the token of a request. `invalidate` is called when the API answered 401 to the one it gave: the
 *  next `token()` is a new one. */
export interface TokenSource {
  token(): Promise<string>
  invalidate?(): void
}

interface Renewal {
  /** The token endpoint of Keycloak (see `keycloakTokenUrl`). */
  tokenUrl: string
  /** For tests: the `fetch` to use, and the clock (milliseconds). */
  fetch?: typeof fetch
  now?: () => number
}

/** The token endpoint of a realm of Keycloak. */
export function keycloakTokenUrl(keycloakUrl: string, realm: string): string {
  return `${keycloakUrl.replace(/\/+$/, '')}/realms/${realm}/protocol/openid-connect/token`
}

/** A token the program has: the text of it, or a function that gives the current one (called for each request, so it can
 *  renew it). It is not renewed here. */
export function bearerToken(token: string | TokenProvider): TokenSource {
  return { token: async () => (typeof token === 'function' ? token() : token) }
}

/** A token got from Keycloak, kept until it is about to run out. Requests that need one at the same time share the call. */
function renewing(options: Renewal, form: () => Promise<Record<string, string>>): TokenSource {
  const now = options.now ?? Date.now
  const http = options.fetch ?? fetch
  let current: { value: string; expires: number } | undefined
  let pending: Promise<string> | undefined

  async function renew(): Promise<string> {
    const response = await http(options.tokenUrl, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(await form()),
    })
    const body = (await response.json().catch(() => ({}))) as {
      access_token?: string
      expires_in?: number
      error?: string
      error_description?: string
    }
    if (!response.ok || !body.access_token) {
      throw new AuthenticationError(
        response.status,
        body.error_description ?? body.error ?? `Keycloak refused the token (${options.tokenUrl}).`,
      )
    }
    current = { value: body.access_token, expires: now() + Math.max((body.expires_in ?? 60) - LEEWAY, 0) * 1000 }
    return current.value
  }

  return {
    async token() {
      if (current && now() < current.expires) return current.value
      pending ??= renew().finally(() => (pending = undefined))
      return pending
    },
    invalidate() {
      current = undefined
    },
  }
}

/** A service account: the application is its own caller (`client_credentials`), with no person behind it. */
export function clientCredentials(
  options: Renewal & { clientId: string; clientSecret: string; scope?: string },
): TokenSource {
  return renewing(options, async () => ({
    grant_type: 'client_credentials',
    client_id: options.clientId,
    client_secret: options.clientSecret,
    ...(options.scope && { scope: options.scope }),
  }))
}

/** The token of a person exchanged (RFC 8693) for one meant for Croquembouche: what is done with it is done as that
 *  person. `subjectToken` is their token, or a function that gives the current one (it is asked for again each time the
 *  exchanged token is renewed). */
export function tokenExchange(
  options: Renewal & {
    clientId: string
    clientSecret: string
    subjectToken: string | TokenProvider
    audience?: string
  },
): TokenSource {
  return renewing(options, async () => ({
    grant_type: TOKEN_EXCHANGE,
    client_id: options.clientId,
    client_secret: options.clientSecret,
    subject_token: typeof options.subjectToken === 'function' ? await options.subjectToken() : options.subjectToken,
    subject_token_type: ACCESS_TOKEN,
    requested_token_type: ACCESS_TOKEN,
    audience: options.audience ?? 'croquembouche-backend',
  }))
}
