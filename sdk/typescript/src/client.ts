import { type TokenSource, bearerToken, clientCredentials } from './auth.js'
import { Analyses } from './analyses.js'
import { createHttp } from './http.js'
import { Searches } from './searches.js'
import { Tasks } from './tasks.js'
import { Templates } from './templates.js'

export interface CroquembouchOptions {
  /** How to sign in: any of `bearerToken`, `clientCredentials` or `tokenExchange` (they renew themselves). */
  auth?: TokenSource
  /** A token the program has (it is not renewed). */
  token?: string
  /** A service account: the token endpoint of Keycloak (see `keycloakTokenUrl`), with `clientId` and `clientSecret`. */
  tokenUrl?: string
  clientId?: string
  clientSecret?: string
  /** How long a request may take, in milliseconds. 30 seconds by default. */
  timeoutMs?: number
  /** The `fetch` to use: the global one by default. */
  fetch?: typeof fetch
}

/** A client of the API::
 *
 *      const client = new Croquembouche(url, { tokenUrl, clientId, clientSecret })
 *      const form = await client.templates.get(templateId)
 *      const run = await client.analyses.run(analysisId, 'scan.pdf')
 *      const result = await run.wait()
 *
 *  How it signs in, from the least to the most to say: nothing (a backend that asks for nothing), `token` (one the program
 *  has), `tokenUrl` with `clientId` and `clientSecret` (a service account, which gets its own token and renews it), or
 *  `auth` with any of `bearerToken`, `clientCredentials` or `tokenExchange`. */
export class Croquembouche {
  readonly templates: Templates
  readonly analyses: Analyses
  readonly searches: Searches
  readonly tasks: Tasks

  constructor(url: string, options: CroquembouchOptions = {}) {
    let auth = options.auth
    if (!auth) {
      if (options.token !== undefined) auth = bearerToken(options.token)
      else if (options.tokenUrl || options.clientId || options.clientSecret) {
        if (!(options.tokenUrl && options.clientId && options.clientSecret)) {
          throw new TypeError('A service account needs tokenUrl, clientId and clientSecret together.')
        }
        auth = clientCredentials({
          tokenUrl: options.tokenUrl,
          clientId: options.clientId,
          clientSecret: options.clientSecret,
          fetch: options.fetch,
        })
      }
    }
    const http = createHttp({ baseUrl: url, auth, fetch: options.fetch, timeoutMs: options.timeoutMs })
    this.templates = new Templates(http)
    this.analyses = new Analyses(http, this.templates)
    this.searches = new Searches(http)
    this.tasks = new Tasks(http)
  }
}
