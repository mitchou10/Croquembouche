import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadGroups, resetGroups, useGroups } from './useGroups'

describe('the groups, as the backend gives them', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    resetGroups()
  })

  it('loads them once, with a name and a number of members each', async () => {
    resetGroups()
    await loadGroups()
    const { groups } = useGroups()
    expect(groups.value.map((g) => g.name)).toEqual(['Équipe courriers', 'Préfecture de Paris', 'Service contentieux', 'Direction'])
    expect(groups.value.every((g) => g.members > 0)).toBe(true)
  })

  it('shows whatever the backend sends', async () => {
    resetGroups()
    const api = await import('../data/api')
    vi.spyOn(api, 'fetchGroups').mockResolvedValue([{ id: 'x', name: 'Autre', members: 3 }])
    await loadGroups()
    expect(useGroups().groups.value).toEqual([{ id: 'x', name: 'Autre', members: 3 }])
  })

  it('asks the backend only once, however many ask', async () => {
    resetGroups()
    const api = await import('../data/api')
    const fetch = vi.spyOn(api, 'fetchGroups')
    await Promise.all([loadGroups(), loadGroups(), loadGroups()])
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('has none, and tries again next time, when the backend cannot be reached', async () => {
    resetGroups()
    const api = await import('../data/api')
    const fetch = vi.spyOn(api, 'fetchGroups').mockRejectedValueOnce(new Error('down'))
    await loadGroups()
    expect(useGroups().groups.value).toEqual([])
    await loadGroups()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(useGroups().groups.value.length).toBeGreaterThan(0)
  })
})
