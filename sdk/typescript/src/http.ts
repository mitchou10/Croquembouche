// The connection: the typed client of `openapi-fetch` (its types come from the OpenAPI of the backend), with the token put
// on every request and an error status turned into the error that says so.
import createClient from 'openapi-fetch'
import type { TokenSource } from './auth.js'
import { errorFor } from './errors.js'
import type { paths } from './generated/schema.js'

export interface HttpOptions {
  baseUrl: string
  auth?: TokenSource
  /** The `fetch` to use: the global one by default. */
  fetch?: typeof fetch
  /** How long a request may take before it is given up, in milliseconds. */
  timeoutMs?: number
}

export type Http = ReturnType<typeof createHttp>

export function createHttp(options: HttpOptions) {
  const { auth, timeoutMs = 30_000 } = options
  const base = options.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args))

  async function send(request: Request): Promise<Response> {
    if (auth) request.headers.set('authorization', `Bearer ${await auth.token()}`)
    const signal = AbortSignal.any([...(request.signal ? [request.signal] : []), AbortSignal.timeout(timeoutMs)])
    return base(new Request(request, { signal }))
  }

  // A 401 is answered by asking for a new token, once: the one that was given may have been revoked.
  async function authenticated(request: Request): Promise<Response> {
    const again = auth?.invalidate ? request.clone() : undefined
    const response = await send(request)
    if (response.status === 401 && again) {
      auth!.invalidate!()
      return send(again)
    }
    return response
  }

  return createClient<paths>({ baseUrl: options.baseUrl.replace(/\/+$/, ''), fetch: authenticated })
}

/** What an answer gave, or the error it is. */
export async function ok<T>(call: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await call
  if (!response.ok) throw errorFor(response.status, error, response.statusText)
  return data as T
}
