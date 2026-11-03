import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import type { TemplateFields } from '../data/mock'
import {
  changedFields,
  cleanCategories,
  documentError,
  MAX_COMMENT_LENGTH,
  MAX_DOCUMENT_BYTES,
  MAX_EXAMPLES,
  cleanList,
  newEntity,
  resetCatalogue,
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

describe('useCatalogue', () => {
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('alice.martin')
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

  it('suggests the usual categories, then the ones already made up, without duplicates', () => {
    const { create, knownCategories } = useCatalogue()
    expect(knownCategories.value).toContain('Tampon')
    expect(knownCategories.value).toContain('Officiel') // from the demo data
    create(fields({ categories: ['tampon', 'Sur mesure'] }))
    expect(knownCategories.value.filter((c) => c.toLowerCase() === 'tampon')).toHaveLength(1)
    expect(knownCategories.value).toContain('Sur mesure')
  })

  it('cleans the categories it is given', () => {
    const { create } = useCatalogue()
    expect(create(fields({ categories: [' Tampon ', 'tampon', ''] }))!.categories).toEqual(['Tampon'])
  })

  it('makes the creator the owner and puts the template first', () => {
    const { create, templates } = useCatalogue()
    const created = create(fields({ name: '  Nouveau  ' }))!
    expect(created).toMatchObject({ name: 'Nouveau', ownerId: 'alice.martin', stars: [], suggestions: [] })
    expect(templates.value[0]).toBe(created)
  })

  it('needs a signed-in user to create or star', () => {
    useSession().setUser(null)
    const { create, toggleStar } = useCatalogue()
    expect(create(fields())).toBeNull()
    expect(toggleStar('t1')).toBe(false)
  })

  it('stars and unstars for the current user only', () => {
    const { find, toggleStar, isStarred } = useCatalogue()
    const template = find('t3')!
    expect(isStarred(template)).toBe(false)
    toggleStar('t3')
    expect(template.stars).toEqual(['alice.martin'])
    toggleStar('t3')
    expect(template.stars).toEqual([])
    expect(toggleStar('nope')).toBe(false)
  })

  it('lets only the owner edit directly', () => {
    const { find, update } = useCatalogue()
    expect(update('t3', fields({ name: 'Signature v2' }))).toBe(true)
    expect(find('t3')!.name).toBe('Signature v2')
    expect(update('t2', fields({ name: 'Piraté' }))).toBe(false) // owned by bob.durand
    expect(find('t2')!.name).toBe('Tampon « Reçu »')
    expect(update('nope', fields())).toBe(false)
  })

  it('lets anyone but the owner suggest a change, which changes nothing until accepted', () => {
    const { find, suggest } = useCatalogue()
    const suggestion = suggest('t2', fields({ name: 'Tampon « Reçu » v2' }), '  plus clair  ')!
    expect(suggestion).toMatchObject({ authorId: 'alice.martin', status: 'pending', message: 'plus clair' })
    expect(find('t2')!.name).toBe('Tampon « Reçu »')
    expect(find('t2')!.suggestions[0]).toBe(suggestion)
  })

  it('refuses a suggestion from the owner, an empty one, or for an unknown template', () => {
    const { suggest } = useCatalogue()
    expect(suggest('t3', fields({ name: 'x' }), '')).toBeNull() // alice owns t3
    const t2 = useCatalogue().find('t2')!
    expect(suggest('t2', { ...t2 }, '')).toBeNull() // nothing changed
    expect(suggest('nope', fields(), '')).toBeNull()
  })

  it('applies an accepted suggestion and keeps a rejected one out', () => {
    const { find, suggest, resolveSuggestion } = useCatalogue()
    useSession().setUser('bob.durand')
    const a = suggest('t3', fields({ name: 'Signature acceptée' }), '')!
    const b = suggest('t3', fields({ name: 'Signature refusée' }), '')!
    useSession().setUser('alice.martin')
    expect(resolveSuggestion('t3', a.id, true)).toBe(true)
    expect(find('t3')!.name).toBe('Signature acceptée')
    expect(a.status).toBe('accepted')
    expect(resolveSuggestion('t3', b.id, false)).toBe(true)
    expect(find('t3')!.name).toBe('Signature acceptée')
    expect(b.status).toBe('rejected')
    expect(resolveSuggestion('t3', a.id, false)).toBe(false) // already decided
  })

  it('lets only the owner decide on a suggestion', () => {
    const { find, suggest, resolveSuggestion, pendingSuggestions } = useCatalogue()
    useSession().setUser('bob.durand')
    const s = suggest('t3', fields({ name: 'Autre nom' }), '')!
    expect(resolveSuggestion('t3', s.id, true)).toBe(false)
    expect(find('t3')!.name).not.toBe('Autre nom')
    expect(pendingSuggestions(find('t3')!)).toContain(s)
    expect(resolveSuggestion('t3', 'nope', true)).toBe(false)
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
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('alice.martin')
  })

  it('creates a template with entities and an optional document', () => {
    const { create } = useCatalogue()
    const doc = { name: 'a.png', type: 'image/png', url: 'blob:a' }
    const withDoc = create(fields({ entities: [{ ...newEntity(), name: ' Date ', definition: ' La date ' }] }), doc)!
    expect(withDoc.document).toEqual(doc)
    expect(withDoc.entities[0]).toMatchObject({ name: 'Date', definition: 'La date' })
    expect(create(fields())!.document).toBeUndefined()
  })

  it('keeps, replaces or removes the document on update, releasing the old blob', () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const { create, update, find } = useCatalogue()
    const t = create(fields(), { name: 'a.png', type: 'image/png', url: 'blob:a' })!

    expect(update(t.id, fields({ name: 'Autre nom' }))).toBe(true) // undefined: untouched
    expect(find(t.id)!.document?.url).toBe('blob:a')
    expect(revoke).not.toHaveBeenCalled()

    update(t.id, fields(), { name: 'b.pdf', type: 'application/pdf', url: 'blob:b' })
    expect(find(t.id)!.document?.url).toBe('blob:b')
    expect(revoke).toHaveBeenCalledWith('blob:a')

    update(t.id, fields(), null)
    expect(find(t.id)!.document).toBeUndefined()
    expect(revoke).toHaveBeenCalledWith('blob:b')
    revoke.mockRestore()
  })

  it('does not try to release a document that is not a blob', () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const { update } = useCatalogue()
    update('t1', fields(), null) // the demo document is a data: URL
    expect(revoke).not.toHaveBeenCalled()
    revoke.mockRestore()
  })

  it('applies the entities of an accepted suggestion', () => {
    const { suggest, resolveSuggestion, find } = useCatalogue()
    useSession().setUser('bob.durand')
    const entity = { ...newEntity(), name: 'Cachet', definition: 'Le cachet' }
    const s = suggest('t3', fields({ name: 'Signature type', description: 'Signature manuscrite de référence.', categories: ['Signature'], entities: [entity] }), '')!
    useSession().setUser('alice.martin')
    resolveSuggestion('t3', s.id, true)
    expect(find('t3')!.entities.map((e) => e.name)).toEqual(['Cachet'])
  })
})

describe('stars on entities', () => {
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('alice.martin')
  })

  it('stars and unstars an entity for the current user only', () => {
    const { find, toggleEntityStar } = useCatalogue()
    const entity = find('t4')!.entities[0]
    expect(entity.stars).toEqual([])
    expect(toggleEntityStar('t4', entity.id)).toBe(true)
    expect(entity.stars).toEqual(['alice.martin'])
    useSession().setUser('bob.durand')
    toggleEntityStar('t4', entity.id)
    expect(entity.stars).toEqual(['alice.martin', 'bob.durand'])
    toggleEntityStar('t4', entity.id)
    expect(entity.stars).toEqual(['alice.martin'])
  })

  it('needs someone signed in, and an entity that exists', () => {
    const { toggleEntityStar } = useCatalogue()
    expect(toggleEntityStar('t4', 'nope')).toBe(false)
    expect(toggleEntityStar('nope', 'e4')).toBe(false)
    useSession().setUser(null)
    expect(toggleEntityStar('t4', 'e4')).toBe(false)
  })

  it('does not count stars as part of what a suggestion changes', () => {
    const entity = { id: 'e', name: 'Date', definition: 'La date', type: 'date' as const, examples: [], stars: ['a'] }
    expect(changedFields(fields({ entities: [entity] }), fields({ entities: [{ ...entity, stars: ['a', 'b'] }] }))).toEqual([])
  })

  it('keeps the stars an entity has now when its owner edits the model', () => {
    const { find, toggleEntityStar, update } = useCatalogue()
    useSession().setUser('chloe.petit') // owns t4
    const t = find('t4')!
    const copy = JSON.parse(JSON.stringify(t.entities)) // what the form holds while it is open
    toggleEntityStar('t4', copy[0].id) // someone stars it meanwhile
    copy[0].name = 'Renommée'
    update('t4', fields({ ...t, entities: copy }))
    expect(find('t4')!.entities[0]).toMatchObject({ name: 'Renommée', stars: ['chloe.petit'] })
  })

  it('keeps them too when a suggestion is accepted, and starts a new entity without any', () => {
    const { find, suggest, resolveSuggestion, toggleEntityStar } = useCatalogue()
    useSession().setUser('dana')
    const t = find('t4')!
    const proposed = [{ ...t.entities[0], name: 'Autre nom' }, { ...newEntity(), name: 'Nouvelle', definition: 'Une de plus' }]
    const s = suggest('t4', { ...fields(), name: t.name, description: t.description, categories: t.categories, entities: proposed }, '')!
    useSession().setUser('chloe.petit') // owner of t4
    toggleEntityStar('t4', t.entities[0].id)
    resolveSuggestion('t4', s.id, true)
    expect(find('t4')!.entities.map((e) => [e.name, e.stars])).toEqual([
      ['Autre nom', ['chloe.petit']],
      ['Nouvelle', []],
    ])
  })
})

describe('comments on a suggestion', () => {
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('dana')
  })

  it('lets anyone signed in comment, trimming the text and dating it', () => {
    const { find, addComment } = useCatalogue()
    const comment = addComment('t1', 's1', '  Pourquoi pas ?  ')!
    expect(comment).toMatchObject({ authorId: 'dana', text: 'Pourquoi pas ?' })
    expect(comment.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(find('t1')!.suggestions[0].comments.at(-1)).toBe(comment)
  })

  it('refuses a blank comment, an unknown suggestion, or no one signed in', () => {
    const { find, addComment } = useCatalogue()
    const before = find('t1')!.suggestions[0].comments.length
    expect(addComment('t1', 's1', '   ')).toBeNull()
    expect(addComment('t1', 'nope', 'Bonjour')).toBeNull()
    expect(addComment('nope', 's1', 'Bonjour')).toBeNull()
    useSession().setUser(null)
    expect(addComment('t1', 's1', 'Bonjour')).toBeNull()
    expect(find('t1')!.suggestions[0].comments).toHaveLength(before)
  })

  it('cuts a comment that is too long', () => {
    const { addComment } = useCatalogue()
    expect(addComment('t1', 's1', 'x'.repeat(MAX_COMMENT_LENGTH + 50))!.text).toHaveLength(MAX_COMMENT_LENGTH)
  })

  it('starts a new suggestion without comments, and lets it be commented whatever its status', () => {
    const { find, suggest, resolveSuggestion, addComment } = useCatalogue()
    const s = suggest('t3', { name: 'Autre', description: 'Autre', categories: [], entities: [] }, '')!
    expect(s.comments).toEqual([])
    useSession().setUser('alice.martin')
    resolveSuggestion('t3', s.id, false)
    expect(addComment('t3', s.id, 'Désolé, non.')).not.toBeNull()
    expect(find('t3')!.suggestions[0].comments).toHaveLength(1)
  })
})

describe('stars on suggestions', () => {
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('dana')
  })

  it('stars and unstars a suggestion for the current user only', () => {
    const { find, toggleSuggestionStar } = useCatalogue()
    const suggestion = find('t1')!.suggestions[0]
    expect(suggestion.stars).toEqual(['chloe.petit'])
    expect(toggleSuggestionStar('t1', 's1')).toBe(true)
    expect(suggestion.stars).toEqual(['chloe.petit', 'dana'])
    toggleSuggestionStar('t1', 's1')
    expect(suggestion.stars).toEqual(['chloe.petit'])
  })

  it('is open to the owner and to the author too, and whatever the status', () => {
    const { find, suggest, resolveSuggestion, toggleSuggestionStar } = useCatalogue()
    const s = suggest('t3', { name: 'Autre', description: 'Autre', categories: [], entities: [] }, '')!
    expect(s.stars).toEqual([])
    expect(toggleSuggestionStar('t3', s.id)).toBe(true) // its author
    useSession().setUser('alice.martin') // the owner
    resolveSuggestion('t3', s.id, false)
    expect(toggleSuggestionStar('t3', s.id)).toBe(true)
    expect(find('t3')!.suggestions[0].stars).toEqual(['dana', 'alice.martin'])
  })

  it('needs someone signed in, and a suggestion that exists', () => {
    const { toggleSuggestionStar } = useCatalogue()
    expect(toggleSuggestionStar('t1', 'nope')).toBe(false)
    expect(toggleSuggestionStar('nope', 's1')).toBe(false)
    useSession().setUser(null)
    expect(toggleSuggestionStar('t1', 's1')).toBe(false)
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

  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('alice.martin')
  })

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

  it('cleans the examples when a model is saved: trimmed, without blanks or duplicates, at most five', () => {
    const { create } = useCatalogue()
    const examples = [' 1 ', '', '2', '2', ' 3', '4', '5', '6', '7']
    const created = create(fields({ entities: [{ ...entity, examples }] }))!
    expect(created.entities[0].examples).toEqual(['1', '2', '3', '4', '5'])
    expect(created.entities[0].examples).toHaveLength(MAX_EXAMPLES)
  })

  it('keeps the type and the examples when the owner edits the model', () => {
    const { find, update } = useCatalogue()
    const t = find('t1')!
    const copy = JSON.parse(JSON.stringify(t.entities))
    copy[0].type = 'amount'
    copy[0].examples = ['1 250,00 €']
    update('t1', fields({ name: t.name, description: t.description, categories: t.categories, entities: copy }))
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
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
  })

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

  it('accepts a suggestion on a model it does not own, which then changes', () => {
    const { find, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    expect(resolveSuggestion('t1', 's1', true)).toBe(true)
    expect(find('t1')!.suggestions[0].status).toBe('accepted')
    expect(find('t1')!.description).toBe('Bloc-marque de la République française, version couleur.')
  })

  it('refuses a suggestion too, which then changes nothing', () => {
    const { find, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    expect(resolveSuggestion('t1', 's1', false)).toBe(true)
    expect(find('t1')!.suggestions[0].status).toBe('rejected')
    expect(find('t1')!.description).toBe('Bloc-marque de la République française.')
  })

  it('still cannot edit a model it does not own, nor decide twice', () => {
    const { find, update, resolveSuggestion } = useCatalogue()
    useSession().setUser('admin', { isAdmin: true })
    const t1 = find('t1')!
    expect(update('t1', { name: 'Piraté', description: t1.description, categories: t1.categories, entities: t1.entities })).toBe(false)
    resolveSuggestion('t1', 's1', true)
    expect(resolveSuggestion('t1', 's1', false)).toBe(false)
  })
})

describe('filtering the models by owner', () => {
  beforeEach(() => {
    localStorage.clear()
    resetCatalogue()
    useSession().setUser('alice.martin')
  })

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

  it('counts a model just made as one of one\'s own', () => {
    const { create, filter } = useCatalogue()
    useSession().setUser('dana')
    const made = create({ name: 'Mien', description: 'À moi', categories: [], entities: [] })!
    expect(filter('', true).map((t) => t.id)).toEqual([made.id])
  })
})
