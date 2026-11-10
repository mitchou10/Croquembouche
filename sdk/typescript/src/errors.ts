// What goes wrong, as errors that say what: the API answers with a status and a `detail`, which is kept.

/** Anything the SDK throws on purpose. */
export class CroquembouchError extends Error {
  override name = 'CroquembouchError'
}

/** The API refused, or failed. `status` is its answer and `detail` the reason it gave, for a person to read. */
export class APIError extends CroquembouchError {
  override name = 'APIError'
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`${status}: ${detail}`)
  }
}

/** 401: no token, a token that is not valid (or is no longer), or a token Keycloak would not give. */
export class AuthenticationError extends APIError {
  override name = 'AuthenticationError'
}

/** 403: the token is good but may not do this (a service account that reads the catalogue changes nothing). */
export class ForbiddenError extends APIError {
  override name = 'ForbiddenError'
}

/** 404: there is no such thing, or it is not for this token to know of (a model it cannot use does not exist). */
export class NotFoundError extends APIError {
  override name = 'NotFoundError'
}

/** 400 or 422: what was sent cannot be kept; `detail` says why. */
export class InvalidRequestError extends APIError {
  override name = 'InvalidRequestError'
}

/** 409: what is asked cannot be done in the state things are in (a model an analysis uses is not deleted). */
export class ConflictError extends APIError {
  override name = 'ConflictError'
}

/** 5xx: the API failed. */
export class ServerError extends APIError {
  override name = 'ServerError'
}

/** What was waited for (a use of an analysis, a search) did not end in time. It goes on, on the server: it can be
 *  waited for again, or cancelled. */
export class WaitTimeoutError extends CroquembouchError {
  override name = 'WaitTimeoutError'
}

/** The use of the analysis ended as failed (the worker could not match the document). */
export class RunFailedError extends CroquembouchError {
  override name = 'RunFailedError'
}

/** The reason in an answer of the API: its `detail`, which is a text, or a list of what is not valid. */
export function detailOf(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body) return body
  const detail = (body as { detail?: unknown } | null | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join('.')}: ${d.msg ?? ''}`.replace(/^: /, ''))
      .join('; ')
  }
  return fallback
}

/** The error for an answer that is an error. */
export function errorFor(status: number, body: unknown, fallback = ''): APIError {
  const detail = detailOf(body, fallback)
  if (status === 401) return new AuthenticationError(status, detail)
  if (status === 403) return new ForbiddenError(status, detail)
  if (status === 404) return new NotFoundError(status, detail)
  if (status === 409) return new ConflictError(status, detail)
  if (status === 400 || status === 422) return new InvalidRequestError(status, detail)
  if (status >= 500) return new ServerError(status, detail)
  return new APIError(status, detail)
}
