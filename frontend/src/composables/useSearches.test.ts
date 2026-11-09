import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../data/api'
import { useSession } from './useSession'
import { resetSearches, useSearches } from './useSearches'

const file = (name: string, type = 'image/png') => new File(['x'], name, { type })

describe('the searches for similar documents', () => {
  beforeEach(() => {
    resetSearches()
    useSession().setUser('alice')
  })
  afterEach(() => vi.useRealTimers())

  it('starts a search, which is the open one and is at the top of the list', async () => {
    const { start, opened, searches } = useSearches()
    const search = await start(file('facture.png'), 4, null)
    expect(search).toMatchObject({ fileName: 'facture.png', k: 4, templateIds: null, status: 'done', pages: 1 })
    expect(opened.value?.id).toBe(search.id)
    expect(searches.value[0]).toMatchObject({ id: search.id, neighbourCount: search.neighbours.length })
    expect(searches.value[0]).not.toHaveProperty('neighbours')
  })

  it('looks for as many neighbours as asked for each page of a PDF, and says which page each looks like', async () => {
    const { start } = useSearches()
    const search = await start(file('dossier.pdf', 'application/pdf'), 2, null)
    expect(search.pages).toBe(3)
    for (const page of [1, 2, 3]) expect(search.links.filter((l) => l.source === `page-${page}`).length).toBeLessThanOrEqual(2)
  })

  it('looks only in the models given', async () => {
    const { start } = useSearches()
    const search = await start(file('facture.png'), 6, ['ghost'])
    expect(search.templateIds).toEqual(['ghost'])
    expect(search.neighbours).toEqual([])
  })

  it('is running while the worker computes, and followed until it has answered', async () => {
    vi.useFakeTimers()
    const { start, opened } = useSearches()
    const started = await start(file('slow.png'), 6, null)
    expect(started).toMatchObject({ status: 'running', neighbours: [], consumption: null })
    await vi.advanceTimersByTimeAsync(2000) // asked for once: not answered yet
    expect(opened.value?.status).toBe('running')
    await vi.advanceTimersByTimeAsync(2000) // asked for again: the worker has answered
    expect(opened.value).toMatchObject({ status: 'done', consumption: { energyWh: 2.4 } })
  })

  it('is followed to the end when the worker fails', async () => {
    vi.useFakeTimers()
    const { start, opened, searches } = useSearches()
    await start(file('broken.png'), 6, null)
    await vi.advanceTimersByTimeAsync(4000)
    expect(opened.value?.status).toBe('failed')
    expect(searches.value[0].status).toBe('failed')
  })

  it('lists the searches that were made, the newest first, and opens one again', async () => {
    const first = await useSearches().start(file('un.png'), 3, null)
    await useSearches().start(file('deux.png'), 3, null)
    resetSearches() // another visit
    const { load, searches, open, opened } = useSearches()
    await load()
    expect(searches.value.map((s) => s.fileName)).toEqual(['deux.png', 'un.png'])
    await open(first.id)
    expect(opened.value).toMatchObject({ id: first.id, fileName: 'un.png' })
  })

  it('does not open the search of someone else', async () => {
    const { id } = await useSearches().start(file('un.png'), 3, null)
    resetSearches()
    useSession().setUser('bob')
    await expect(useSearches().open(id)).rejects.toMatchObject({ status: 404 })
    await useSearches().load()
    expect(useSearches().searches.value).toEqual([])
  })

  it('deletes a search', async () => {
    const { start, remove, searches, opened } = useSearches()
    const { id } = await start(file('un.png'), 3, null)
    expect(await remove(id)).toBe('')
    expect(searches.value).toEqual([])
    expect(opened.value).toBeNull()
    expect(await remove(id)).toBe('') // already gone: nothing to say
  })

  it('refuses what is not an image or a PDF, with the reason', async () => {
    await expect(useSearches().start(file('notes.txt', 'text/plain'), 3, null)).rejects.toBeInstanceOf(ApiError)
  })

  it('says the list could not be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('down'))))
    const { load, failed, loaded } = useSearches()
    await load()
    expect(failed.value).toBe(true)
    expect(loaded.value).toBe(true)
  })
})
