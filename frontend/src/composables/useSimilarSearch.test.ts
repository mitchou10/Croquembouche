import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { findNeighbours } from '../data/similar'
import { useSimilarSearch } from './useSimilarSearch'

const png = (name = 'facture.png', size = 10) => new File([new Uint8Array(size)], name, { type: 'image/png' })

function setup() {
  let search!: ReturnType<typeof useSimilarSearch>
  const wrapper = mount(defineComponent({ setup() { search = useSimilarSearch(); return () => h('div') } }))
  return { search, wrapper }
}

describe('the search for similar documents', () => {
  beforeEach(() => {
    let blobs = 0
    URL.createObjectURL = vi.fn(() => `blob:test-${++blobs}`)
    URL.revokeObjectURL = vi.fn()
  })

  it('finds k neighbours, the likeliest first, each with a picture', async () => {
    const { search } = setup()
    await search.search(png())
    const neighbours = search.found.value!.neighbours
    expect(neighbours).toHaveLength(6)
    expect(neighbours.map((n) => n.similarity)).toEqual([...neighbours.map((n) => n.similarity)].sort((a, b) => b - a))
    expect(neighbours.every((n) => n.imageUrl.startsWith('data:image/svg+xml'))).toBe(true)
  })

  it('gives the same answer for the same file', async () => {
    expect(await findNeighbours(png(), 5)).toEqual(await findNeighbours(png(), 5))
    expect(await findNeighbours(png('autre.png'), 5)).not.toEqual(await findNeighbours(png(), 5))
  })

  it('links only neighbours that exist', async () => {
    const { neighbours, links } = await findNeighbours(png(), 10)
    const ids = new Set(neighbours.map((n) => n.id))
    expect(links.every((l) => ids.has(l.source) && ids.has(l.target) && l.source !== l.target)).toBe(true)
  })

  it('shows an image as itself and a PDF as a sheet', async () => {
    const { search } = setup()
    await search.search(png())
    expect(search.previewUrl.value).toBe('blob:test-1')
    await search.search(new File(['x'], 'a.pdf', { type: 'application/pdf' }))
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-1')
    expect(search.previewUrl.value.startsWith('data:image/svg+xml')).toBe(true)
  })

  it('searches again when the number wanted changes, within the limits', async () => {
    const { search } = setup()
    await search.search(png())
    await search.setK(3)
    expect(search.found.value!.neighbours).toHaveLength(3)
    await search.setK(99)
    expect(search.k.value).toBe(12)
    await search.setK(-4)
    expect(search.k.value).toBe(1)
    await search.setK(Number.NaN)
    expect(search.k.value).toBe(6)
  })

  it('does not search when there is no file yet', async () => {
    const { search } = setup()
    await search.setK(4)
    expect(search.found.value).toBeNull()
  })

  it('forgets everything on reset, and lets go of the picture when the page is left', async () => {
    const { search, wrapper } = setup()
    await search.search(png())
    search.reset()
    expect(search.file.value).toBeNull()
    expect(search.found.value).toBeNull()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-1')
    await search.search(png())
    wrapper.unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-2')
    await flushPromises()
  })
})
