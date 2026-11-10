import { describe, expect, it } from 'vitest'
import { WaitTimeoutError } from '../src/index.js'
import { FakeAPI, Seq } from './fake.js'

const search = (status = 'running', neighbours: unknown[] = []) => ({
  id: 's1',
  fileName: 'scan.pdf',
  status,
  k: 5,
  templateIds: null,
  createdAt: '2026-11-10T10:00:00Z',
  pages: 1,
  neighbourCount: neighbours.length,
  neighbours,
  links: [],
})
const NEIGHBOUR = { id: 't1:1', templateId: 't1', templatePage: 1, documentId: 'd1', similarity: 0.93 }
const PDF = new TextEncoder().encode('%PDF')

describe('searches', () => {
  it('starts a search and waits for it', async () => {
    const api = new FakeAPI()
    api.on('POST /api/searches', search(), 201)
    api.on('GET /api/searches/s1', new Seq([search(), search('done', [NEIGHBOUR])]))

    const started = await api.client().searches.start(PDF, { k: 3, templateIds: ['t1', 't2'], filename: 'scan.pdf' })
    const found = await started.wait({ intervalMs: 0 })

    const form = await api.requests('POST /api/searches')[0]!.formData()
    expect(form.get('k')).toBe('3')
    expect(form.getAll('templateIds')).toEqual(['t1', 't2'])
    expect(found.status).toBe('done')
    expect(found.neighbours.map((n) => [n.templateId, n.similarity])).toEqual([['t1', 0.93]])
  })

  it('does not name a model when it looks in every one', async () => {
    const api = new FakeAPI()
    api.on('POST /api/searches', search(), 201)

    await api.client().searches.start(PDF)

    expect((await api.seen[0]!.formData()).has('templateIds')).toBe(false)
  })

  it('times out when the search does not end', async () => {
    const api = new FakeAPI()
    api.on('POST /api/searches', search(), 201)
    api.on('GET /api/searches/s1', search())

    const started = await api.client().searches.start(PDF)

    await expect(started.wait({ timeoutMs: 50, intervalMs: 10 })).rejects.toBeInstanceOf(WaitTimeoutError)
  })
})
