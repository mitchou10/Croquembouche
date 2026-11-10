import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ForbiddenError, RunFailedError, WaitTimeoutError } from '../src/index.js'
import { FakeAPI, Seq, analysis, detection, entity, run, template } from './fake.js'

const RUNS = '/api/analyses/a1/runs'
const PDF = new TextEncoder().encode('%PDF')
const quickly = { intervalMs: 0 }

function started(api: FakeAPI, ...later: unknown[]) {
  api.on(`POST ${RUNS}`, run('running'), 201)
  api.on(`GET ${RUNS}/r1`, new Seq(later))
  api.on('GET /api/analyses/a1', analysis())
  api.on('GET /api/templates/t1', template())
}

describe('analyses', () => {
  it('pins some models to a version', async () => {
    const api = new FakeAPI()
    api.on('POST /api/analyses', analysis({ templateVersions: { t1: '1.0.0' } }), 201)

    const made = await api.client().analyses.create('Courriers', ['t1', 't2'], { templateVersions: { t1: '1.0.0' } })

    expect(await FakeAPI.body(api.seen[0]!)).toEqual({
      name: 'Courriers',
      templateIds: ['t1', 't2'],
      description: '',
      isPublic: false,
      shares: [],
      templateVersions: { t1: '1.0.0' },
    })
    expect(made.templateVersions).toEqual({ t1: '1.0.0' })
  })

  it('tries a document and waits for its result', async () => {
    const api = new FakeAPI()
    const path = join(mkdtempSync(join(tmpdir(), 'sdk-')), 'scan.pdf')
    writeFileSync(path, '%PDF-1')
    started(
      api,
      run('running'),
      run('done', { detections: [detection({ text: '2026-0042' }), detection({ id: 'd2', entityId: 'e9', text: null })] }),
    )

    const pending = await api.client().analyses.run('a1', path, { keepScreenshot: true })
    const result = await pending.wait(quickly)

    const form = await api.requests(`POST ${RUNS}`)[0]!.formData()
    expect((form.get('file') as File).name).toBe('scan.pdf')
    expect(await (form.get('file') as File).text()).toBe('%PDF-1')
    expect(form.get('keepScreenshot')).toBe('true')
    expect(pending.status).toBe('done')
    expect(result.status).toBe('done')
    expect(api.requests(`GET ${RUNS}/r1`)).toHaveLength(2)
    const [found, unknown] = result.elements
    // What was found is named by the entity of the model it is, and says what is written there.
    expect([found?.entity?.name, found?.text, found?.confidence]).toEqual(['Numéro', '2026-0042', 0.9])
    expect(found?.template?.name).toBe('Formulaire')
    expect(found?.zone.page).toBe(1)
    expect(found?.zoneIndex).toBeUndefined()
    expect(unknown?.entity).toBeUndefined() // an entity the token cannot read, or that is gone
    expect(unknown?.text).toBeUndefined()
    expect(result.pages.map((p) => p.page)).toEqual([1])
  })

  it('waits for the text to be read unless told not to', async () => {
    const api = new FakeAPI()
    const open = (extra: object) => run('done', { detections: [detection({ text: null })], ...extra })
    started(
      api,
      open({ ocrStatus: 'running' }),
      open({ ocrStatus: 'done', findStatus: 'running' }),
      run('done', { ocrStatus: 'done', findStatus: 'done', detections: [detection({ text: 'lu' })] }),
    )
    const client = api.client()

    const result = await (await client.analyses.run('a1', PDF)).wait(quickly)
    expect(result.elements[0]?.text).toBe('lu')
    expect(api.requests(`GET ${RUNS}/r1`)).toHaveLength(3)

    api.seen.length = 0
    api.on(`GET ${RUNS}/r1`, open({ ocrStatus: 'running' }))
    const quick = await (await client.analyses.run('a1', PDF)).wait({ ...quickly, text: false })
    expect(quick.elements[0]?.text).toBeUndefined()
    expect(api.requests(`GET ${RUNS}/r1`)).toHaveLength(1)
  })

  it('tells apart the zones of an entity that has several', async () => {
    const api = new FakeAPI()
    started(api, run('done', { detections: [detection({ zoneIndex: 0 }), detection({ id: 'd2', zoneIndex: 1 })] }))

    const result = await (await api.client().analyses.run('a1', PDF)).wait(quickly)

    expect(result.elements.map((e) => [e.entity?.id, e.zoneIndex])).toEqual([['e1', 0], ['e1', 1]])
  })

  it('names the entities of sub-models too', async () => {
    const api = new FakeAPI()
    started(api, run('done', { detections: [detection({ entityId: 'e2', classifications: [{ templateId: 't2', confidence: 0.8 }] })] }))
    api.on('GET /api/templates/t1', template('t1', 'Formulaire', { children: [{ id: 't2', name: 'Annexe', version: '1.0.0' }] }))
    api.on('GET /api/templates/t2', template('t2', 'Annexe', { entities: [entity('e2', 'Date')] }))

    const [element] = (await (await api.client().analyses.run('a1', PDF)).wait(quickly)).elements

    expect([element?.entity?.name, element?.template?.name]).toEqual(['Date', 'Annexe'])
  })

  it('times out, and the use can be cancelled', async () => {
    const api = new FakeAPI()
    started(api, run('running'))
    api.on(`POST ${RUNS}/r1/cancel`, run('cancelled'))
    const pending = await api.client().analyses.run('a1', PDF)

    await expect(pending.wait({ timeoutMs: 50, intervalMs: 10 })).rejects.toBeInstanceOf(WaitTimeoutError)
    expect(pending.ended).toBe(false)

    expect((await pending.cancel()).status).toBe('cancelled')
    expect(pending.ended).toBe(true)
  })

  it('gives up waiting when told to', async () => {
    const api = new FakeAPI()
    started(api, run('running'))
    const pending = await api.client().analyses.run('a1', PDF)
    const controller = new AbortController()

    const waiting = pending.wait({ intervalMs: 1000, signal: controller.signal })
    setTimeout(() => controller.abort(new Error('enough')), 20)

    await expect(waiting).rejects.toThrow('enough')
  })

  it('throws when the use failed, and ends the wait of one that was cancelled', async () => {
    const api = new FakeAPI()
    started(api, run('failed'))
    await expect((await api.client().analyses.run('a1', PDF)).wait(quickly)).rejects.toBeInstanceOf(RunFailedError)

    api.on(`GET ${RUNS}/r1`, run('cancelled'))
    const result = await (await api.client().analyses.run('a1', PDF)).wait(quickly)
    expect(result.status).toBe('cancelled')
    expect(result.elements).toEqual([])
  })

  it('leaves the entities unnamed when the token cannot read the model', async () => {
    const api = new FakeAPI()
    started(api, run('done', { detections: [detection()] }))
    api.on('GET /api/templates/t1', { detail: 'Not found' }, 404)

    const [element] = (await (await api.client().analyses.run('a1', PDF)).wait(quickly)).elements

    expect(element?.entity).toBeUndefined()
    expect(element?.template).toBeUndefined()
    expect(element?.text).toBe('42')
  })

  it('refuses a service account that only reads what it may not write', async () => {
    const api = new FakeAPI()
    api.on('POST /api/templates', { detail: 'Ce compte de service est en lecture seule.' }, 403)

    const error = await api.client().templates.create({ name: 'x' }).catch((e) => e)

    expect(error).toBeInstanceOf(ForbiddenError)
    expect(error.detail).toMatch(/lecture seule/)
  })
})
