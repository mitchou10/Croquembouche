import { computed, ref } from 'vue'
import {
  defaultCategories,
  type Comment,
  templates as seed,
  type Suggestion,
  type Template,
  type TemplateDocument,
  type TemplateEntity,
  type TemplateFields,
} from '../data/mock'
import { entityTypeLabel } from './useEntityTypes'
import { useSession } from './useSession'

// In memory only, like the analyses: reloading the page restores the seed until the backend exists.
const templates = ref<Template[]>(structuredClone(seed))

/** Back to the demo data. For the tests, which would otherwise see what the previous one left behind. */
export function resetCatalogue() {
  templates.value = structuredClone(seed)
}

let sequence = 0
const newId = (prefix: string) => `${prefix}${Date.now()}-${++sequence}`
const today = () => new Date().toISOString().slice(0, 10)

export const newEntity = (): TemplateEntity => ({
  id: newId('e'),
  name: '',
  definition: '',
  type: 'text',
  examples: [],
  stars: [],
})

export const MAX_EXAMPLES = 5
export const MAX_EXAMPLE_LENGTH = 60


/** A document is an image or a PDF, nothing else, and not an unreasonable size. */
export const ACCEPTED_DOCUMENT_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'application/pdf']
export const MAX_COMMENT_LENGTH = 500
export const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024

/** Returns the reason a file can't be used as a model's document, or null when it can. */
export function documentError(file: { type: string; size: number }): string | null {
  if (!ACCEPTED_DOCUMENT_TYPES.includes(file.type)) return 'Le document doit être une image (PNG, JPEG, WebP, GIF) ou un PDF.'
  if (file.size > MAX_DOCUMENT_BYTES) return 'Le document ne doit pas dépasser 20 Mo.'
  return null
}

/** Zones are drawn on images. A PDF has no preview here: it will be shown through screenshots of its pages. */
export const isImage = (document: { type: string } | null | undefined) => !!document?.type.startsWith('image/')

export function toDocument(file: File): TemplateDocument {
  return { name: file.name, type: file.type, url: URL.createObjectURL(file) }
}

const textFieldLabels = { name: 'Nom', description: 'Description' } as const

const withoutStars = ({ stars: _stars, ...rest }: TemplateEntity) => rest

/** Replaces the entities, keeping the stars they have now: stars are not something an edit or a suggestion carries. */
const keepStars = (current: TemplateEntity[], incoming: TemplateEntity[]): TemplateEntity[] =>
  incoming.map((e) => ({ ...e, stars: current.find((c) => c.id === e.id)?.stars ?? [] }))

const describeList = (items: string[]) => (items.length ? items.join(', ') : 'Aucune')
// Name, then what else sets one entity apart from another: its type, a zone, its examples.
const describeEntities = (entities: TemplateEntity[]) =>
  describeList(
    entities.map((e) => {
      const details = [entityTypeLabel(e.type).toLowerCase(), ...(e.zone ? ['zone'] : [])].join(', ')
      return `${e.name} (${details})${e.examples.length ? ` ex. ${e.examples.join(' / ')}` : ''}`
    }),
  )

/** Trimmed, without blanks or duplicates, in the order given. Case counts as a difference unless told otherwise. */
export function cleanList(values: string[], ignoreCase = false): string[] {
  const key = (v: string) => (ignoreCase ? v.toLowerCase() : v)
  const seen = new Set<string>()
  return values.map((v) => v.trim()).filter((v) => v && !seen.has(key(v)) && seen.add(key(v)))
}

/** Categories: « tampon » is « Tampon ». */
export const cleanCategories = (categories: string[]) => cleanList(categories, true)

export interface FieldChange {
  label: string
  before: string
  after: string
}

/** What `fields` would change on `template`. */
export function changedFields(template: TemplateFields, fields: TemplateFields): FieldChange[] {
  const changes: FieldChange[] = (Object.keys(textFieldLabels) as (keyof typeof textFieldLabels)[])
    .filter((key) => template[key] !== fields[key])
    .map((key) => ({ label: textFieldLabels[key], before: template[key], after: fields[key] }))
  if (JSON.stringify(template.categories) !== JSON.stringify(fields.categories)) {
    changes.push({
      label: 'Catégories',
      before: describeList(template.categories),
      after: describeList(fields.categories),
    })
  }
  // Entities carry a definition and a zone too: compared whole (their stars are not part of what is proposed), shown by name.
  if (JSON.stringify(template.entities.map(withoutStars)) !== JSON.stringify(fields.entities.map(withoutStars))) {
    changes.push({
      label: 'Entités',
      before: describeEntities(template.entities),
      after: describeEntities(fields.entities),
    })
  }
  return changes
}

function clean(fields: TemplateFields): TemplateFields {
  return {
    name: fields.name.trim(),
    description: fields.description.trim(),
    categories: cleanCategories(fields.categories),
    entities: fields.entities.map((e) => ({
      ...e,
      name: e.name.trim(),
      definition: e.definition.trim(),
      examples: cleanList(e.examples).slice(0, MAX_EXAMPLES),
    })),
  }
}

const revoke = (document?: TemplateDocument) => document?.url.startsWith('blob:') && URL.revokeObjectURL(document.url)

export function useCatalogue() {
  const { userId, isAdmin } = useSession()

  /** What can be suggested as a category: the usual ones, then whatever others have already made up. */
  const knownCategories = computed(() =>
    cleanCategories([...defaultCategories, ...templates.value.flatMap((t) => t.categories)]),
  )

  const find = (id: string) => templates.value.find((t) => t.id === id)
  const isOwner = (template: Template) => userId.value !== null && template.ownerId === userId.value
  /** Who accepts or refuses the suggestions made on a model: its owner, and an administrator on any model. */
  const canDecide = (template: Template) => isOwner(template) || isAdmin.value
  const isStarred = (template: Template) => userId.value !== null && template.stars.includes(userId.value)
  const pendingSuggestions = (template: Template) => template.suggestions.filter((s) => s.status === 'pending')
  const templateName = (id: string) => find(id)?.name ?? 'Modèle inconnu'

  /** Models matching a search, and only the signed-in user's own when `mine` is set. */
  function filter(query: string, mine = false): Template[] {
    const q = query.trim().toLowerCase()
    return templates.value.filter(
      (t) =>
        (!mine || isOwner(t)) &&
        (!q || [t.name, t.description, ...t.categories].some((field) => field.toLowerCase().includes(q))),
    )
  }

  /** The signed-in user becomes the owner. Newest first. */
  function create(fields: TemplateFields, document?: TemplateDocument): Template | null {
    if (userId.value === null) return null
    const template: Template = {
      id: newId('t'),
      ownerId: userId.value,
      stars: [],
      suggestions: [],
      ...(document && { document }),
      ...clean(fields),
    }
    templates.value = [template, ...templates.value]
    return find(template.id)!
  }

  function toggleStar(id: string): boolean {
    const template = find(id)
    if (!template || userId.value === null) return false
    template.stars = isStarred(template)
      ? template.stars.filter((u) => u !== userId.value)
      : [...template.stars, userId.value]
    return true
  }

  /** Anyone signed in can star an entity, as a model: it says which ones are worth looking for. */
  function toggleEntityStar(id: string, entityId: string): boolean {
    const entity = find(id)?.entities.find((e) => e.id === entityId)
    if (!entity || userId.value === null) return false
    entity.stars = entity.stars.includes(userId.value)
      ? entity.stars.filter((u) => u !== userId.value)
      : [...entity.stars, userId.value]
    return true
  }

  /** Anyone signed in can star a suggestion, whatever its status, its author and the owner included. */
  function toggleSuggestionStar(id: string, suggestionId: string): boolean {
    const suggestion = find(id)?.suggestions.find((s) => s.id === suggestionId)
    if (!suggestion || userId.value === null) return false
    suggestion.stars = suggestion.stars.includes(userId.value)
      ? suggestion.stars.filter((u) => u !== userId.value)
      : [...suggestion.stars, userId.value]
    return true
  }

  /** Only the owner edits a template directly. `document`: undefined keeps it, null removes it. */
  function update(id: string, fields: TemplateFields, document?: TemplateDocument | null): boolean {
    const template = find(id)
    if (!template || !isOwner(template)) return false
    const cleaned = clean(fields)
    Object.assign(template, cleaned, { entities: keepStars(template.entities, cleaned.entities) })
    if (document !== undefined) {
      revoke(template.document)
      template.document = document ?? undefined
    }
    return true
  }

  /** Anyone but the owner can propose a change; it waits for the owner's decision. */
  function suggest(id: string, fields: TemplateFields, message: string): Suggestion | null {
    const template = find(id)
    if (!template || userId.value === null || isOwner(template)) return null
    const proposed = clean(fields)
    if (changedFields(template, proposed).length === 0) return null
    const suggestion: Suggestion = {
      id: newId('s'),
      authorId: userId.value,
      fields: proposed,
      message: message.trim(),
      date: today(),
      status: 'pending',
      comments: [],
      stars: [],
    }
    template.suggestions = [suggestion, ...template.suggestions]
    return template.suggestions[0]
  }

  /** Anyone signed in can comment a suggestion, whatever its status; a blank comment is not one. */
  function addComment(id: string, suggestionId: string, text: string): Comment | null {
    const suggestion = find(id)?.suggestions.find((s) => s.id === suggestionId)
    const trimmed = text.trim()
    if (!suggestion || !trimmed || userId.value === null) return null
    suggestion.comments = [
      ...suggestion.comments,
      { id: newId('c'), authorId: userId.value, text: trimmed.slice(0, MAX_COMMENT_LENGTH), date: today() },
    ]
    return suggestion.comments[suggestion.comments.length - 1]
  }

  /** Only whoever can decide does (see canDecide); accepting applies the proposed fields. */
  function resolveSuggestion(id: string, suggestionId: string, accept: boolean): boolean {
    const template = find(id)
    const suggestion = template?.suggestions.find((s) => s.id === suggestionId)
    if (!template || !suggestion || !canDecide(template) || suggestion.status !== 'pending') return false
    if (accept) {
      Object.assign(template, suggestion.fields, { entities: keepStars(template.entities, suggestion.fields.entities) })
    }
    suggestion.status = accept ? 'accepted' : 'rejected'
    return true
  }

  return {
    templates,
    knownCategories,
    find,
    isOwner,
    canDecide,
    isStarred,
    pendingSuggestions,
    templateName,
    filter,
    create,
    toggleStar,
    toggleEntityStar,
    toggleSuggestionStar,
    addComment,
    update,
    suggest,
    resolveSuggestion,
  }
}
