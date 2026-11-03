import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../data/api'
import type { TemplateFields } from '../data/mock'
import {
  changedFields,
  cleanCategories,
  documentError,
  MAX_DOCUMENT_BYTES,
  MAX_EXAMPLES,
  cleanList,
  loadCatalogue,
  newEntity,
  resetCatalogue,
  toBody,
  useCatalogue,
} from './useCatalogue'
import { loadEntityTypes, entityTypeLabel, entityTypeDefinition, resetEntityTypes, useEntityTypes } from './useEntityTypes'
import { useSession } from './useSession'

const fields = (over: Partial<TemplateFields> = {}): TemplateFields => ({
  name: 'Nouveau',
  description: 'Un modèle',
  categories: ['Autre'],
  entities: [],
  ...over,
})


// Every describe starts from the demo catalogue, as the (fake) backend has it, with someone signed in.
const signIn = async (user: string | null = 'alice.martin', details: { isAdmin?: boolean } = {}) => {
  resetCatalogue()
  useSession().setUser(user, details)
  await loadCatalogue()
}
const refused = async (call: Promise<unknown>, status: number) => {
  const error = await call.then(() => null, (e: unknown) => e)
  expect(error).toBeInstanceOf(ApiError)
  expect((error as ApiError).status).toBe(status)
}


describe('useCatalogue', () => {
  beforeEach(() => signIn())

  it('is loaded from the backend, once', async () => {
    const { templates } = useCatalogue()
    expect(templates.value.length).toBeGreaterThan(5)
    expect(templates.value[0].ownerName).toBeDefined()
    const calls = vi.mocked(fetch).mock?.calls.length
    await loadCatalogue()
    expect(vi.mocked(fetch).mock?.calls.length).toBe(calls)
  })

  it('starts empty and tries again later when the backend cannot be reached', async () => {
    resetCatalogue()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const { templates, failed } = useCatalogue()
    await loadCatalogue()
    expect(templates.value).toEqual([])
    expect(failed.value).toBe(true)
    // The next use asks again.
    vi.stubGlobal('fetch', (await import('../test/fakeBackend')).fakeFetch)
    await loadCatalogue()
    expect(failed.value).toBe(false)
    expect(templates.value.length).toBeGreaterThan(5)
  })

  it('filters by name, description and category, ignoring case', () => {
    const { filter, templates } = useCatalogue()
    expect(filter('  ')).toEqual(templates.value)
    expect(filter('marianne').map((t) => t.id)).toContain('t1')
    expect(filter('TAMPON').map((t) => t.categories)).toContainEqual(['Tampon'])
    expect(filter('officiel').map((t) => t.id)).toEqual(['t1', 't8']) // a second tag of two of the models
    expect(filter('zzz')).toEqual([])
  })

  it('falls back on an unknown template name', () => {
    const { templateName } = useCatalogue()
    expect(templateName('t1')).toBe('Logo Marianne')
    expect(templateName('nope')).toBe('Modèle inconnu')
  })

  it('suggests the usual categories, then the ones already made up, without duplicates', async () => {
    const { create, knownCategories } = useCatalogue()
    expect(knownCategories.value).toContain('Tampon')
    expect(knownCategories.value).toContain('Officiel') // from the demo data
    await create(fields({ categories: ['tampon', 'Sur mesure'] }))
    expect(knownCategories.value.filter((c) => c.toLowerCase() === 'tampon')).toHaveLength(1)
    expect(knownCategories.value).toContain('Sur mesure')
  })

  it('makes the creator the owner and puts the template first', async () => {
    const { create, templates } = useCatalogue()
    const created = await create(fields({ name: '  Nouveau  ', categories: [' Tampon ', 'tampon', ''] }))
    expect(created).toMatchObject({ name: 'Nouveau', ownerId: 'alice.martin', stars: [], suggestions: [] })
    expect(created.categories).toEqual(['Tampon'])
    expect(templates.value[0]).toEqual(created)
  })

  it('says what the backend refuses, and whether a small action went through', async () => {
    useSession().setUser(null)
    const { create, toggleStar, actionError } = useCatalogue()
    await refused(create(fields()), 401)
    expect(await toggleStar('t1')).toBe(false)
    expect(actionError.value).toBe('Not authenticated')
    useSession().setUser('alice.martin')
    expect(await toggleStar('t3')).toBe(true)
    expect(actionError.value).toBe('') // cleared by the next action
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect(await toggleStar('t3')).toBe(false)
    expect(actionError.value).toBe('Le serveur est injoignable.')
  })

  it('stars and unstars for the current user only', async () => {
    const { find, toggleStar, isStarred } = useCatalogue()
    expect(isStarred(find('t3')!)).toBe(false)
    await toggleStar('t3')
    expect(find('t3')!.stars).toEqual(['alice.martin'])
    expect(isStarred(find('t3')!)).toBe(true)
    await toggleStar('t3')
    expect(find('t3')!.stars).toEqual([])
    expect(await toggleStar('nope')).toBe(false)
  })

  it('lets only the owner edit directly', async () => {
    const { find, update } = useCatalogue()
    await update('t3', fields({ name: 'Signature v2' }))
    expect(find('t3')!.name).toBe('Signature v2')
    await refused(update('t2', fields({ name: 'Piraté' })), 403) // owned by bob.durand
    expect(find('t2')!.name).toBe('Tampon « Reçu »')
    await refused(update('nope', fields()), 404)
  })

  it('lets anyone but the owner suggest a change, which changes nothing until accepted', async () => {
    const { find, suggest } = useCatalogue()
    const template = await suggest('t2', fields({ name: 'Tampon « Reçu » v2' }), '  plus clair  ')
    expect(template.suggestions[0]).toMatchObject({ authorId: 'alice.martin', status: 'pending', message: 'plus clair' })
    expect(find('t2')!.name).toBe('Tampon « Reçu »')
    expect(find('t2')!.suggestions[0].id).toBe(template.suggestions[0].id)
  })

  it('refuses a suggestion from the owner, an empty one, or for an unknown template', async () => {
    const { suggest, find } = useCatalogue()
    await refused(suggest('t3', fields({ name: 'x' }), ''), 403) // alice owns t3
    await refused(suggest('t2', { ...find('t2')! }, ''), 422) // nothing changed
    await refused(suggest('nope', fields(), ''), 404)
  })

  it('applies an accepted suggestion and keeps a rejected one out', async () => {
    const { find, suggest, resolveSuggestion } = useCatalogue()
    useSession().setUser('bob.durand')
    await suggest('t3', fields({ name: 'Signature acceptée' }), '')
    await suggest('t3', fields({ name: 'Signature refusée' }), '')
    const [b, a] = find('t3')!.suggestions
    useSession().setUser('alice.martin')
    expect(await resolveSuggestion('t3', a.id, true)).toBe(true)
    expect(find('t3')!.name).toBe('Signature acceptée')
    expect(find('t3')!.suggestions.find((s) => s.id === a.id)!.status).toBe('accepted')
    expect(await resolveSuggestion('t3', b.id, false)).toBe(true)
    expect(find('t3')!.name).toBe('Signature acceptée')
    expect(find('t3')!.suggestions.find((s) => s.id === b.id)!.status).toBe('rejected')
    expect(await resolveSuggestion('t3', a.id, false)).toBe(false) // already decided
  })

  it('lets only the owner or an administrator decide on a suggestion', async () => {
    const { find, suggest, resolveSuggestion, pendingSuggestions, actionError } = useCatalogue()
    useSession().setUser('bob.durand')
    await suggest('t3', fields({ name: 'Autre nom' }), '')
    const s = find('t3')!.suggestions[0]
    expect(await resolveSuggestion('t3', s.id, true)).toBe(false)
    expect(actionError.value).toContain('propriétaire')
    expect(find('t3')!.name).not.toBe('Autre nom')
    expect(pendingSuggestions(find('t3')!).map((p) => p.id)).toContain(s.id)
    expect(await resolveSuggestion('t3', 'nope', true)).toBe(false)
  })

  it('deletes a model of one\'s own, and is told why when it cannot', async () => {
    const { create, remove, find, actionError } = useCatalogue()
    const mine = await create(fields())
    expect(await remove(mine.id)).toBe(true)
    expect(find(mine.id)).toBeUndefined()
    expect(await remove('t2')).toBe(false) // bob.durand's
    expect(actionError.value).toContain('propriétaire')
    expect(await remove('t1')).toBe(false) // an analysis looks for it
    expect(actionError.value).toContain('analyse')
    expect(find('t1')).toBeDefined()
    expect(await remove('nope')).toBe(false)
  })

  it('sends the entities with the id they have, and the document by its id', () => {
    const entity = { ...newEntity(), id: 'e1', name: 'Date', examples: ['a'], zone: { page: 2, points: [] } }
    const body = toBody(fields({ entities: [entity] }), 'doc-1')
    expect(body.entities).toEqual([
      { id: 'e1', name: 'Date', definition: '', type: 'text', examples: ['a'], zone: { page: 2, points: [] } },
    ])
    expect(body.documentId).toBe('doc-1')
    expect('documentId' in toBody(fields())).toBe(false) // absent: the document is kept
    expect(toBody(fields(), null).documentId).toBeNull() // null: it is removed
    expect('zone' in toBody(fields({ entities: [{ ...newEntity(), name: 'x' }] })).entities[0]).toBe(false)
  })
})

describe('changedFields', () => {
  it('lists only what differs', () => {
    expect(changedFields(fields(), fields({ description: 'Autre', categories: ['Autre', 'Officiel'] }))).toEqual([
      { label: 'Description', before: 'Un modèle', after: 'Autre' },
      { label: 'Catégories', before: 'Autre', after: 'Autre, Officiel' },
    ])
  })

  it('says so when the categories are emptied', () => {
    expect(changedFields(fields(), fields({ categories: [] }))).toEqual([
      { label: 'Catégories', before: 'Autre', after: 'Aucune' },
    ])
  })
})

describe('cleanCategories', () => {
  it('trims, drops blanks and duplicates (case aside), keeping the first spelling and the order', () => {
    expect(cleanCategories(['  Tampon ', '', 'tampon', 'Identité', '   ', 'TAMPON', 'Autre'])).toEqual([
      'Tampon',
      'Identité',
      'Autre',
    ])
  })
})

describe('changedFields on entities', () => {
  const entity = { id: 'e', stars: [] as string[], type: 'date' as const, examples: [] as string[], name: 'Date', definition: 'La date', zone: { page: 1, points: [{ x: 0, y: 0 }, { x: 0.5, y: 0 }, { x: 0.5, y: 0.5 }] } }

  it('reports added, removed or moved entities by name', () => {
    expect(changedFields(fields(), fields({ entities: [entity] }))).toEqual([
      { label: 'Entités', before: 'Aucune', after: 'Date (date, zone)' },
    ])
    expect(changedFields(fields({ entities: [entity] }), fields({ entities: [{ ...entity, zone: undefined }] }))).toEqual([
      { label: 'Entités', before: 'Date (date, zone)', after: 'Date (date)' },
    ])
  })

  it('reports nothing when the entities are the same', () => {
    expect(changedFields(fields({ entities: [entity] }), fields({ entities: [{ ...entity }] }))).toEqual([])
  })
})

describe('documentError', () => {
  it.each(['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'application/pdf'])('accepts %s', (type) => {
    expect(documentError({ type, size: 1024 })).toBeNull()
  })

  it.each(['text/plain', 'application/zip', 'image/svg+xml', 'application/msword', ''])('refuses %j', (type) => {
    expect(documentError({ type, size: 1024 })).toMatch(/image .* ou un PDF/)
  })

  it('refuses a file over 20 Mo', () => {
    expect(documentError({ type: 'application/pdf', size: MAX_DOCUMENT_BYTES })).toBeNull()
    expect(documentError({ type: 'application/pdf', size: MAX_DOCUMENT_BYTES + 1 })).toMatch(/20 Mo/)
  })
})

describe('documents and entities of a template', () => {
  beforeEach(() => signIn())

  it('creates a template with entities and an optional document', async () => {
    const { create } = useCatalogue()
    const doc = { id: 'd1', name: 'a.png', type: 'image/png', url: '/api/documents/d1/pages/1', pages: 1 }
    const withDoc = await create(fields({ entities: [{ ...newEntity(), name: ' Date ', definition: ' La date ' }] }), doc)
    expect(withDoc.document).toMatchObject({ id: 'd1', type: 'image/png', pages: 1, url: '/api/documents/d1/pages/1' })
    expect(withDoc.entities[0]).toMatchObject({ name: 'Date', definition: 'La date' })
    expect((await create(fields())).document).toBeUndefined()
  })

  it('keeps, replaces or removes the document on update', async () => {
    const { create, update, find } = useCatalogue()
    const t = await create(fields(), { id: 'a', name: 'a.png', type: 'image/png', url: '' })

    await update(t.id, fields({ name: 'Autre nom' })) // undefined: untouched
    expect(find(t.id)!.document?.id).toBe('a')

    await update(t.id, fields(), { id: 'b', name: 'b.pdf', type: 'application/pdf', url: '', pages: 3 })
    expect(find(t.id)!.document?.id).toBe('b')

    await update(t.id, fields(), null)
    expect(find(t.id)!.document).toBeUndefined()
  })

  it('applies the entities of an accepted suggestion', async () => {
    const { suggest, resolveSuggestion, find } = useCatalogue()
    useSession().setUser('bob.durand')
    const entity = { ...newEntity(), name: 'Cachet', definition: 'Le cachet' }
    await suggest('t3', fields({ name: 'Signature type', description: 'Signature manuscrite de référence.', categories: ['Signature'], entities: [entity] }), '')
    useSession().setUser('alice.martin')
    await resolveSuggestion('t3', find('t3')!.suggestions[0].id, true)
    expect(find('t3')!.entities.map((e) => e.name)).toEqual(['Cachet'])
  })
})

describe('stars on entities', () => {
  beforeEach(() => signIn())

  it('stars and unstars an entity for the current user only', async () => {
    const { find, toggleEntityStar } = useCatalogue()
    const id = find('t4')!.entities[0].id
    expect(find('t4')!.entities[0].stars).toEqual([])
    expect(await toggleEntityStar('t4', id)).toBe(true)
    expect(find('t4')!.entities[0].stars).toEqual(['alice.martin'])
    useSession().setUser('bob.durand')
    await toggleEntityStar('t4', id)
    expect(find('t4')!.entities[0].stars).toEqual(['alice.martin', 'bob.durand'])
    await toggleEntityStar('t4', id)
    expect(find('t4')!.entities[0].stars).toEqual(['alice.martin'])
  })

  it('needs someone signed in, and an entity that exists', async () => {
    const { toggleEntityStar } = useCatalogue()
    expect(await toggleEntityStar('t4', 'nope')).toBe(false)
    expect(await toggleEntityStar('nope', 'e4')).toBe(false)
    useSession().setUser(null)
    expect(await toggleEntityStar('t4', 'e4')).toBe(false)
  })

  it('does not count stars as part of what a suggestion changes', () => {
    const entity = { id: 'e', name: 'Date', definition: 'La date', type: 'date' as const, examples: [], stars: ['a'] }
    expect(changedFields(fields({ entities: [entity] }), fields({ entities: [{ ...entity, stars: ['a', 'b'] }] }))).toEqual([])
  })

  it('keeps the stars an entity has now when its owner edits the model', async () => {
    const { find, toggleEntityStar, update } = useCatalogue()
    useSession().setUser('chloe.petit') // owns t4
    const t = find('t4')!
    const copy = JSON.parse(JSON.stringify(t.entities)) // what the form holds while it is open
    await toggleEntityStar('t4', copy[0].id) // someone stars it meanwhile
    copy[0].name = 'Renommée'
    await update('t4', fields({ ...t, entities: copy }))
    expect(find('t4')!.entities[0]).toMatchObject({ name: 'Renommée', stars: ['chloe.petit'] })
  })

  it('keeps them too when a suggestion is accepted, and starts a new entity without any', async () => {
    const { find, suggest, resolveSuggestion, toggleEntityStar } = useCatalogue()
    useSession().setUser('dana')
    const t = find('t4')!
    const proposed = [{ ...t.entities[0], name: 'Autre nom' }, { ...newEntity(), name: 'Nouvelle', definition: 'Une de plus' }]
    await suggest('t4', { ...fields(), name: t.name, description: t.description, categories: t.categories, entities: proposed }, '')
    useSession().setUser('chloe.petit') // owner of t4
    await toggleEntityStar('t4', t.entities[0].id)
    await resolveSuggestion('t4', find('t4')!.suggestions[0].id, true)
    expect(find('t4')!.entities.map((e) => [e.name, e.stars])).toEqual([
      ['Autre nom', ['chloe.petit']],
      ['Nouvelle', []],
    ])
  })
})

describe('comments on a suggestion', () => {
  beforeEach(() => signIn('dana'))

  it('lets anyone signed in comment, with their name and the date', async () => {
    const { find, addComment } = useCatalogue()
    expect(await addComment('t1', 's1', '  Pourquoi pas ?  ')).toBe(true)
    const comment = find('t1')!.suggestions[0].comments.at(-1)!
    expect(comment).toMatchObject({ authorId: 'dana', authorName: 'dana', text: 'Pourquoi pas ?' })
    expect(comment.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('is refused a blank comment, an unknown suggestion, or no one signed in', async () => {
    const { find, addComment } = useCatalogue()
    const before = find('t1')!.suggestions[0].comments.length
    expect(await addComment('t1', 's1', '   ')).toBe(false)
    expect(await addComment('t1', 'nope', 'Bonjour')).toBe(false)
    expect(await addComment('nope', 's1', 'Bonjour')).toBe(false)
    useSession().setUser(null)
    expect(await addComment('t1', 's1', 'Bonjour')).toBe(false)
    expect(find('t1')!.suggestions[0].comments).toHaveLength(before)
  })

  it('lets a suggestion be commented whatever its status', async () => {
    const { find, suggest, resolveSuggestion, addComment } = useCatalogue()
    await suggest('t3', { name: 'Autre', description: 'Autre', categories: [], entities: [] }, '')
    const s = find('t3')!.suggestions[0]
    expect(s.comments).toEqual([])
    useSession().setUser('alice.martin')
    await resolveSuggestion('t3', s.id, false)
    expect(await addComment('t3', s.id, 'Désolé, non.')).toBe(true)
    expect(find('t3')!.suggestions[0].comments).toHaveLength(1)
  })
})

describe('stars on suggestions', () => {
  beforeEach(() => signIn('dana'))

  it('stars and unstars a suggestion for the current user only', async () => {
    const { find, toggleSuggestionStar } = useCatalogue()
    expect(find('t1')!.suggestions[0].stars).toEqual(['chloe.petit'])
    expect(await toggleSuggestionStar('t1', 's1')).toBe(true)
    expect(find('t1')!.suggestions[0].stars).toEqual(['chloe.petit', 'dana'])
    await toggleSuggestionStar('t1', 's1')
    expect(find('t1')!.suggestions[0].stars).toEqual(['chloe.petit'])
  })

  it('is open to the owner and to the author too, and whatever the status', async () => {
    const { find, suggest, resolveSuggestion, toggleSuggestionStar } = useCatalogue()
    await suggest('t3', { name: 'Autre', description: 'Autre', categories: [], entities: [] }, '')
    const id = find('t3')!.suggestions[0].id
    expect(find('t3')!.suggestions[0].stars).toEqual([])
    expect(await toggleSuggestionStar('t3', id)).toBe(true) // its author
    useSession().setUser('alice.martin') // the owner
    await resolveSuggestion('t3', id, false)
    expect(await toggleSuggestionStar('t3', id)).toBe(true)
    expect(find('t3')!.suggestions[0].stars).toEqual(['dana', 'alice.martin'])
  })

  it('needs someone signed in, and a suggestion that exists', async () => {
    const { toggleSuggestionStar } = useCatalogue()
    expect(await toggleSuggestionStar('t1', 'nope')).toBe(false)
    expect(await toggleSuggestionStar('nope', 's1')).toBe(false)
    useSession().setUser(null)
    expect(await toggleSuggestionStar('t1', 's1')).toBe(false)
  })

  it('does not count stars as part of what a suggestion changes', () => {
    const { find } = useCatalogue()
    const s = find('t1')!.suggestions[0]
    expect(changedFields(find('t1')!, s.fields).map((c) => c.label)).toEqual(['Description'])
  })
})

describe('type and examples of an entity', () => {
  beforeAll(loadEntityTypes) // the labels of the types, as the backend gives them

  const entity = { id: 'e', stars: [] as string[], type: 'date' as const, examples: ['12/03/2026'], name: 'Date', definition: 'La date' }

  beforeEach(() => signIn())

  it('starts a new entity as text, with no example', () => {
    expect(newEntity()).toMatchObject({ type: 'text', examples: [] })
  })

  it('names the types, and gives an unknown one back as it is', () => {
    expect(entityTypeLabel('amount')).toBe('Montant')
    expect(entityTypeLabel('yes_no')).toBe('Oui / non')
    expect(entityTypeLabel('weird')).toBe('weird')
  })

  it('shows a change of type or of examples in a suggestion, though the name is the same', () => {
    const before = fields({ entities: [entity] })
    expect(changedFields(before, fields({ entities: [{ ...entity, type: 'amount' }] }))).toEqual([
      { label: 'Entités', before: 'Date (date) ex. 12/03/2026', after: 'Date (montant) ex. 12/03/2026' },
    ])
    expect(changedFields(before, fields({ entities: [{ ...entity, examples: ['12/03/2026', '1 novembre 2026'] }] }))).toEqual([
      { label: 'Entités', before: 'Date (date) ex. 12/03/2026', after: 'Date (date) ex. 12/03/2026 / 1 novembre 2026' },
    ])
  })

  it('cleans the examples when a model is saved: trimmed, without blanks or duplicates, at most five', async () => {
    const { create } = useCatalogue()
    const examples = [' 1 ', '', '2', '2', ' 3', '4', '5', '6', '7']
    const created = await create(fields({ entities: [{ ...entity, examples }] }))
    expect(created.entities[0].examples).toEqual(['1', '2', '3', '4', '5'])
    expect(created.entities[0].examples).toHaveLength(MAX_EXAMPLES)
  })

  it('keeps the type and the examples when the owner edits the model', async () => {
    const { find, update } = useCatalogue()
    const t = find('t1')!
    const copy = JSON.parse(JSON.stringify(t.entities))
    copy[0].type = 'amount'
    copy[0].examples = ['1 250,00 €']
    useSession().setUser('alice.martin')
    await update('t1', fields({ name: t.name, description: t.description, categories: t.categories, entities: copy }))
    expect(find('t1')!.entities[0]).toMatchObject({ type: 'amount', examples: ['1 250,00 €'] })
  })
})

describe('cleanList', () => {
  it('counts case as a difference unless told otherwise', () => {
    expect(cleanList(['a', 'A', ' a '])).toEqual(['a', 'A'])
    expect(cleanList(['a', 'A', ' a '], true)).toEqual(['a'])
  })
})

describe('the types of entity, as the backend gives them', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    resetEntityTypes()
  })

  it('loads them once, with a label and a definition each', async () => {
    resetEntityTypes()
    await loadEntityTypes()
    expect(entityTypeLabel('date')).toBe('Date')
    expect(entityTypeDefinition('amount')).toMatch(/somme d’argent/)
    const { types, loaded } = useEntityTypes()
    expect(loaded.value).toBe(true)
    expect(types.value.map((t) => t.value)).toEqual(['text', 'date', 'integer', 'decimal', 'amount', 'percentage', 'yes_no'])
    expect(types.value.every((t) => t.label && t.definition)).toBe(true)
  })

  it('shows whatever the backend sends, not a list of its own', async () => {
    resetEntityTypes()
    const api = await import('../data/api')
    vi.spyOn(api, 'fetchEntityTypes').mockResolvedValue([{ value: 'siret', label: 'SIRET', definition: 'Numéro à 14 chiffres.' }])
    await loadEntityTypes()
    expect(useEntityTypes().types.value.map((t) => t.value)).toEqual(['siret'])
    expect(entityTypeLabel('siret')).toBe('SIRET')
    expect(entityTypeDefinition('siret')).toBe('Numéro à 14 chiffres.')
  })

  it('falls back on the code, with no definition, for a type it does not know', async () => {
    await loadEntityTypes()
    expect(entityTypeLabel('weird')).toBe('weird')
    expect(entityTypeDefinition('weird')).toBe('')
  })

  it('keeps an entity\'s own type in the options when the backend no longer lists it', async () => {
    await loadEntityTypes()
    const { optionsFor } = useEntityTypes()
    expect(optionsFor('date').filter((o) => o.value === 'date')).toHaveLength(1)
    expect(optionsFor('retired').at(-1)).toEqual({ value: 'retired', text: 'retired (inconnu)' })
    expect(optionsFor('').some((o) => o.text.includes('inconnu'))).toBe(false)
  })

  it('shows the codes, and tries again next time, when the backend cannot be reached', async () => {
    resetEntityTypes()
    const api = await import('../data/api')
    const fetch = vi.spyOn(api, 'fetchEntityTypes').mockRejectedValueOnce(new Error('down'))
    await loadEntityTypes()
    expect(useEntityTypes().failed.value).toBe(true)
    expect(entityTypeLabel('date')).toBe('date')
    await loadEntityTypes() // the second attempt goes through
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(entityTypeLabel('date')).toBe('Date')
  })
})

describe('the administrator', () => {
  beforeEach(() => signIn())

  it('is whoever the backend says is one, and nobody else', () => {
    const session = useSession()
    session.setUser('admin', { isAdmin: true })
    expect(session.isAdmin.value).toBe(true)
    session.setUser('administrateur')
    expect(session.isAdmin.value).toBe(false)
    session.setUser('alice.martin')
    expect(session.isAdmin.value).toBe(false)
    session.setUser(null)
    expect(session.isAdmin.value).toBe(false)
  })

  it('can decide on the suggestions of any model, as can its owner, and nobody else', () => {
    const { find, canDecide } = useCatalogue()
    const t1 = find('t1')! // owned by alice.martin
    useSession().setUser('alice.martin')
    expect(canDecide(t1)).toBe(true)
    useSession().setUser('admin', { isAdmin: true })
    expect(canDecide(t1)).toBe(true)
    expect(canDecide(find('t2')!)).toBe(true)
    useSession().setUser('dana')
    expect(canDecide(t1)).toBe(false)
    useSession().setUser(null)
    expect(canDecide(t1)).toBe(false)
  })

  it('accepts a suggestion on a model it does not own, which then changes', async () => {
    const { find, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    expect(await resolveSuggestion('t1', 's1', true)).toBe(true)
    expect(find('t1')!.suggestions[0].status).toBe('accepted')
    expect(find('t1')!.description).toBe('Bloc-marque de la République française, version couleur.')
  })

  it('refuses a suggestion too, which then changes nothing', async () => {
    const { find, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    expect(await resolveSuggestion('t1', 's1', false)).toBe(true)
    expect(find('t1')!.suggestions[0].status).toBe('rejected')
    expect(find('t1')!.description).toBe('Bloc-marque de la République française.')
  })

  it('still cannot edit a model it does not own, nor decide twice', async () => {
    const { find, update, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    const t1 = find('t1')!
    await refused(update('t1', { name: 'Piraté', description: t1.description, categories: t1.categories, entities: t1.entities }), 403)
    await resolveSuggestion('t1', 's1', true)
    expect(await resolveSuggestion('t1', 's1', false)).toBe(false)
  })
})

describe('filtering the models by owner', () => {
  beforeEach(() => signIn())

  it('keeps only the signed-in user\'s own models', () => {
    const { filter } = useCatalogue()
    expect(filter('', true).map((t) => t.id)).toEqual(['t1', 't3', 't7', 't10'])
    expect(filter('', false).length).toBeGreaterThan(4)
  })

  it('goes with a search', () => {
    const { filter } = useCatalogue()
    expect(filter('logo', true).map((t) => t.id)).toEqual(['t1', 't10'])
    expect(filter('tampon', true).map((t) => t.id)).toEqual(['t7']) // t2 and t6 are others'
    expect(filter('zzz', true)).toEqual([])
  })

  it('changes with who is signed in, and shows nothing to nobody', () => {
    const { filter } = useCatalogue()
    useSession().setUser('bob.durand')
    expect(filter('', true).map((t) => t.id)).toEqual(['t2', 't5', 't8'])
    useSession().setUser('dana')
    expect(filter('', true)).toEqual([])
    useSession().setUser(null)
    expect(filter('', true)).toEqual([])
  })

  it('counts a model just made as one of one\'s own', async () => {
    const { create, filter } = useCatalogue()
    useSession().setUser('dana')
    const made = await create({ name: 'Mien', description: 'À moi', categories: [], entities: [] })
    expect(filter('', true).map((t) => t.id)).toEqual([made.id])
  })
})
