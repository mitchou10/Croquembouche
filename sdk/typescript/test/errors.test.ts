import { describe, expect, it } from 'vitest'
import {
  APIError,
  AuthenticationError,
  ConflictError,
  ForbiddenError,
  InvalidRequestError,
  NotFoundError,
  ServerError,
} from '../src/index.js'
import { FakeAPI } from './fake.js'

describe('errors', () => {
  it.each([
    [401, AuthenticationError],
    [403, ForbiddenError],
    [404, NotFoundError],
    [409, ConflictError],
    [422, InvalidRequestError],
    [400, InvalidRequestError],
    [500, ServerError],
    [503, ServerError],
    [418, APIError],
  ] as const)('an error status %i is the error that says so', async (status, kind) => {
    const api = new FakeAPI()
    api.on('GET /api/templates/t1', { detail: 'Pas pour vous.' }, status)

    const error = await api.client().templates.get('t1').catch((e) => e)

    expect(error).toBeInstanceOf(kind)
    expect(error.constructor).toBe(kind)
    expect(error).toMatchObject({ status, detail: 'Pas pour vous.' })
  })

  it('lists what is not valid in the detail', async () => {
    const api = new FakeAPI()
    api.on('POST /api/templates', { detail: [{ loc: ['body', 'name'], msg: 'Field required', type: 'missing' }] }, 422)

    const error = await api.client().templates.create({ name: '' } as never).catch((e) => e)

    expect(error).toBeInstanceOf(InvalidRequestError)
    expect(error.detail).toBe('body.name: Field required')
  })

  it('gives the text of an answer that is not JSON', async () => {
    const api = new FakeAPI()
    api.on('GET /api/templates/t1', 'Bad gateway', 502)

    const error = await api.client().templates.get('t1').catch((e) => e)

    expect(error).toBeInstanceOf(ServerError)
    expect(error.detail).toBe('Bad gateway')
  })
})
