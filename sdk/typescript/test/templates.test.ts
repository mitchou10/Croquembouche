import { writeFileSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { FakeAPI, SQUARE, entity, template } from './fake.js'

describe('templates', () => {
  it('lists and searches the catalogue', async () => {
    const api = new FakeAPI()
    api.on('GET /api/templates', [template(), template('t2', 'Facture')])

    const listed = await api.client().templates.list('fact', { mine: true })

    expect(listed.map((t) => t.name)).toEqual(['Formulaire', 'Facture'])
    expect(Object.fromEntries(new URL(api.seen[0]!.url).searchParams)).toEqual({ q: 'fact', mine: 'true' })
  })

  it('has the entities of a model with their zones', async () => {
    const api = new FakeAPI()
    const two = [SQUARE, { ...SQUARE, page: 2 }]
    api.on('GET /api/templates/t1', template('t1', 'F', { entities: [entity('e1', 'Numéro', two), entity('e2', 'Libre', [])] }))

    const form = await api.client().templates.get('t1')

    const [numero, libre] = form.entities
    expect(numero?.zones?.map((z) => z.page)).toEqual([1, 2])
    expect(numero?.zones?.[0]?.points[0]?.x).toBe(0.1)
    expect(libre?.zones).toEqual([])
    expect(form.version).toBe('1.0.0')
  })

  it('reads the versions of a model and the image of a page', async () => {
    const api = new FakeAPI()
    api.on('GET /api/templates/t1/versions', [{ version: '1.0.1', date: '2026-11-10', authorId: 'a', authorName: 'A' }])
    api.on('GET /api/templates/t1/pages/2', new Uint8Array([0x89, 0x50, 0x4e, 0x47]))
    const client = api.client()

    expect((await client.templates.versions('t1')).map((v) => v.version)).toEqual(['1.0.1'])
    const image = await client.templates.page('t1', 2)
    expect([...image]).toEqual([0x89, 0x50, 0x4e, 0x47])
    expect(new URL(api.seen.at(-1)!.url).searchParams.has('documentId')).toBe(false)

    await client.templates.page('t1', 2, { documentId: 'd0' })
    expect(new URL(api.seen.at(-1)!.url).searchParams.get('documentId')).toBe('d0')
  })

  it('makes a model with the names of the API', async () => {
    const api = new FakeAPI()
    api.on('POST /api/templates', template('t9', 'Neuf'), 201)

    const made = await api.client().templates.create({
      name: 'Neuf',
      entities: [{ name: 'Numéro', type: 'text', zones: [SQUARE] }],
    })

    const sent = await FakeAPI.body(api.seen[0]!)
    expect(made.id).toBe('t9')
    expect(sent).toMatchObject({ name: 'Neuf', entities: [{ type: 'text', zones: [{ page: 1 }] }] })
  })

  it('says who a model is shared with', async () => {
    const api = new FakeAPI()
    api.on('PUT /api/templates/t1/shares', template('t1', 'F', { visibility: 'shared' }))

    await api.client().templates.share('t1', 'shared', [{ kind: 'group', value: 'team' }])

    expect(await FakeAPI.body(api.seen[0]!)).toEqual({ visibility: 'shared', shares: [{ kind: 'group', value: 'team' }] })
  })

  it('deletes a model and says which sub-model takes its place', async () => {
    const api = new FakeAPI()
    api.on('DELETE /api/templates/t1', null, 204)
    const client = api.client()

    await client.templates.delete('t1')
    expect(new URL(api.seen[0]!.url).searchParams.has('promote')).toBe(false)
    await client.templates.delete('t1', { promoteChild: 't2' })
    expect(new URL(api.seen[1]!.url).searchParams.get('promote')).toBe('t2')
  })

  it('sends a document from bytes, a File, or the path of a file', async () => {
    const api = new FakeAPI()
    api.on('POST /api/documents', { id: 'd1', name: 'a.pdf', contentType: 'application/pdf', pages: 2 }, 201)
    const path = join(mkdtempSync(join(tmpdir(), 'sdk-')), 'a.pdf')
    writeFileSync(path, '%PDF-path')
    const client = api.client()

    const documents = [
      [new TextEncoder().encode('%PDF-bytes'), { filename: 'a.pdf' }, '%PDF-bytes'],
      [new File(['%PDF-file'], 'a.pdf'), {}, '%PDF-file'],
      [path, {}, '%PDF-path'],
    ] as const
    for (const [document, options, content] of documents) {
      const sent = await client.templates.uploadDocument(document, options)
      const form = await api.seen.at(-1)!.formData()
      const file = form.get('file') as File
      expect(sent.id).toBe('d1')
      expect(file.name).toBe('a.pdf')
      expect(file.type).toBe('application/pdf')
      expect(await file.text()).toBe(content)
    }
  })
})
