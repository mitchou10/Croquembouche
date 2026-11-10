import { describe, expect, it } from 'vitest'
import { NotFoundError } from '../src/index.js'
import { FakeAPI } from './fake.js'

const task = (name = 'template_matching.classify_pages', version = '1.25.0', online = 1) => ({
  name,
  version,
  description: 'What each page is',
  author: 'Croquembouche',
  inputSchema: { type: 'object', properties: { template_ids: { type: 'array' } } },
  parameters: { type: 'object', properties: { threshold: { type: 'number', default: 0.8 } } },
  outputSchema: { type: 'array' },
  createdAt: '2026-11-10T10:00:00Z',
  online,
  instances: [
    {
      instanceId: 'template_matching-host-ab12',
      service: 'template_matching',
      hostname: 'host',
      startedAt: '2026-11-10T10:00:00Z',
      lastSeenAt: '2026-11-10T10:01:00Z',
      online: online > 0,
    },
  ],
})

describe('tasks', () => {
  it('lists the tasks of the workers with their schemas', async () => {
    const api = new FakeAPI()
    api.on('GET /api/tasks', [task(), task('ocr.read_document', '1.25.0', 0)])

    const [first, second] = await api.client().tasks.list({ online: true })

    expect(new URL(api.seen[0]!.url).searchParams.get('online')).toBe('true')
    expect([first?.name, first?.version, first?.online, first?.author]).toEqual([
      'template_matching.classify_pages',
      '1.25.0',
      1,
      'Croquembouche',
    ])
    expect(first?.inputSchema).toEqual({ type: 'object', properties: { template_ids: { type: 'array' } } })
    expect(first?.parameters).toMatchObject({ properties: { threshold: { default: 0.8 } } })
    expect(first?.outputSchema).toEqual({ type: 'array' })
    expect(first?.instances[0]).toMatchObject({ instanceId: 'template_matching-host-ab12', online: true })
    expect(second?.online).toBe(0)
    expect(second?.instances[0]?.online).toBe(false)
  })

  it('reads the versions of a task by name', async () => {
    const api = new FakeAPI()
    api.on('GET /api/tasks/template_matching.classify_pages', [task('template_matching.classify_pages', '1.24.0'), task()])
    api.on('GET /api/tasks/unknown', { detail: 'Not found' }, 404)
    const client = api.client()

    const versions = await client.tasks.get('template_matching.classify_pages')

    expect(versions.map((t) => t.version)).toEqual(['1.24.0', '1.25.0'])
    expect(new URL(api.seen[0]!.url).searchParams.get('online')).toBe('false')
    await expect(client.tasks.get('unknown')).rejects.toBeInstanceOf(NotFoundError)
  })
})
