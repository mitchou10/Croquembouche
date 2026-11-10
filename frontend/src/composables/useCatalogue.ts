import { computed, ref } from 'vue'
import * as api from '../data/api'
import {
  defaultCategories,
  type Share,
  type Template,
  type TemplateDocument,
  type TemplateEntity,
  type PageFields,
  type TemplateFields,
  type Visibility,
} from '../data/mock'
import { entityTypeLabel } from './useEntityTypes'
import { useSession } from './useSession'

// The catalogue as the backend has it, loaded once and then kept up to date with what its answers say.
const templates = ref<Template[]>([])
const failed = ref(false)
let loading: Promise<void> | null = null

export function loadCatalogue(): Promise<void> {
  loading ??= api
    .fetchTemplates()
    .then((list) => {
      templates.value = list
      failed.value = false
    })
    .catch(() => {
      // The page still works, empty: and the next use tries again.
      failed.value = true
      loading = null
    })
  return loading
}

/** Forgets what was loaded. For the tests, which would otherwise see what the previous one left behind. */
export function resetCatalogue() {
  templates.value = []
  failed.value = false
  actionError.value = ''
  loading = null
}

// What the last small action (a star, a comment, a decision) was refused for, to show on the page; cleared by the next.
const actionError = ref('')

/** Runs an action whose refusal is shown on the page rather than in a form; says whether it went through. */
async function attempt(run: () => Promise<unknown>): Promise<boolean> {
  actionError.value = ''
  try {
    await run()
    return true
  } catch (error) {
    actionError.value = error instanceof api.ApiError ? error.message : 'Le serveur est injoignable.'
    return false
  }
}

let sequence = 0
const newId = (prefix: string) => `${prefix}${Date.now()}-${++sequence}`

export const newEntity = (): TemplateEntity => ({
  id: newId('e'),
  name: '',
  definition: '',
  type: 'text',
  examples: [],
  tags: [],
  zones: [],
  stars: [],
})

export const MAX_EXAMPLES = 5
export const MAX_EXAMPLE_LENGTH = 60
export const MAX_TAGS = 10
/** The most zones an entity can have. */
export const MAX_ZONES = 10
export const MAX_TAG_LENGTH = 30


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

/** Zones are drawn on images; a PDF is shown through the screenshots of its pages that the backend makes. */
export const isImage = (document: { type: string } | null | undefined) => !!document?.type.startsWith('image/')

/** What the viewer can show and draw on: an image, or an uploaded document, whose pages the backend gives as images. */
export const canPreview = (document: { id?: string; type: string } | null | undefined) =>
  !!document && (!!document.id || isImage(document))

const textFieldLabels = { name: 'Nom', description: 'Description' } as const

const withoutStars = ({ stars: _stars, ...rest }: TemplateEntity) => rest

const describeList = (items: string[]) => (items.length ? items.join(', ') : 'Aucune')
// Name, then what else sets one entity apart from another: its type, a zone, its examples, its tags.
const describeEntities = (entities: TemplateEntity[]) =>
  describeList(
    entities.map((e) => {
      const details = [entityTypeLabel(e.type).toLowerCase(), ...(e.zones.length ? [e.zones.length > 1 ? `${e.zones.length} zones` : 'zone'] : [])].join(', ')
      return `${e.name} (${details})${e.examples.length ? ` ex. ${e.examples.join(' / ')}` : ''}${e.tags.length ? ` #${e.tags.join(' #')}` : ''}`
    }),
  )

const describePages = (pages: PageFields[]) =>
  describeList(givenPages(pages).map((p) => `page ${p.page}${p.name.trim() ? ` : ${p.name.trim()}` : ''}`))

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
  const pagesOf = (pages: PageFields[]) => JSON.stringify(givenPages(pages).map((p) => [p.page, p.name.trim(), p.description.trim()]))
  if (pagesOf(template.pages ?? []) !== pagesOf(fields.pages ?? [])) {
    changes.push({
      label: 'Pages',
      before: describePages(template.pages ?? []),
      after: describePages(fields.pages ?? []),
    })
  }
  return changes
}

/** The pages that were given a name or a description. */
export const givenPages = (pages: PageFields[]) => pages.filter((p) => p.name.trim() || p.description.trim())

/** What the backend takes of a model's fields. The entities keep the id they have: that is how it knows them. */
export function toBody(fields: TemplateFields, documentId?: string | null, sharing?: Sharing): api.TemplateBody {
  return {
    name: fields.name,
    description: fields.description,
    categories: fields.categories,
    // Only what was said: a page without a name or a description is the default.
    pages: givenPages(fields.pages),
    entities: fields.entities.map((e) => ({
      id: e.id,
      name: e.name,
      definition: e.definition,
      type: e.type,
      examples: e.examples,
      tags: e.tags,
      ...(e.zones.length && { zones: e.zones }),
    })),
    ...(documentId !== undefined && { documentId }),
    ...(sharing && { visibility: sharing.visibility, shares: sharing.visibility === 'shared' ? sharing.shares : [] }),
  }
}

/** Who a model is for, as the form says it. */
export interface Sharing {
  visibility: Visibility
  shares: Share[]
}

export function useCatalogue() {
  const { userId, isAdmin } = useSession()
  void loadCatalogue()

  /** What can be suggested as a category: the usual ones, then whatever others have already made up. */
  const knownCategories = computed(() =>
    cleanCategories([...defaultCategories, ...templates.value.flatMap((t) => t.categories)]),
  )

  const find = (id: string) => templates.value.find((t) => t.id === id)
  const isOwner = (template: Template) => userId.value !== null && template.ownerId === userId.value
  /** Who accepts or refuses the suggestions made on a model: its owner, and an administrator on any model. */
  const canDecide = (template: Template) => isOwner(template) || isAdmin.value
  const isStarred = (template: Template) => userId.value !== null && template.stars.some((s) => s === userId.value)
  const pendingSuggestions = (template: Template) => template.suggestions.filter((s) => s.status === 'pending')
  const templateName = (id: string) => find(id)?.name ?? 'Modèle inconnu'
  /** How a page of a model is called: its name, else the name of the model and its number; the model's for no page. */
  const pageLabel = (id: string, page?: number | null) => {
    const template = find(id)
    if (!template) return 'Modèle inconnu'
    return (page && template.pages.find((p) => p.page === page)?.label) || template.name
  }

  /** Models matching a search, and only the signed-in user's own when `mine` is set. */
  function filter(query: string, mine = false): Template[] {
    const q = query.trim().toLowerCase()
    // The sub-models show under their model (on its page); they are listed on their own when one is searched for.
    return templates.value.filter(
      (t) =>
        (!mine || isOwner(t)) &&
        (q ? [t.name, t.description, ...t.categories].some((field) => field.toLowerCase().includes(q)) : t.parentId === null),
    )
  }

  /** Puts what the backend answered in the catalogue, where the model was or at the top when it is new. */
  function keep(template: Template): Template {
    const index = templates.value.findIndex((t) => t.id === template.id)
    if (index === -1) templates.value = [template, ...templates.value]
    else templates.value = templates.value.map((t, i) => (i === index ? template : t))
    return template
  }

  // Every change is the backend's to accept or refuse (who may do it, what is valid). The forms' (create, update,
  // suggest) throw an `ApiError` saying why; the small actions say whether they went through, and `actionError` why not.

  /** The signed-in user becomes the owner. Newest first. */
  const create = async (fields: TemplateFields, document?: TemplateDocument, parentId?: string, sharing?: Sharing) => {
    const created = keep(await api.postTemplate({ ...toBody(fields, document?.id ?? undefined, sharing), ...(parentId && { parentId }) }))
    // The parent lists it from now on.
    if (created.parentId) updateChildren(created.parentId, (children) => [...children, { id: created.id, name: created.name, version: created.version }])
    return created
  }

  /** Changes the list of sub-models a model shows, without asking the backend again. */
  function updateChildren(id: string, change: (children: Template['children']) => Template['children']) {
    templates.value = templates.value.map((t) => (t.id === id ? { ...t, children: change(t.children) } : t))
  }

  /** Only the owner deletes a model, and not one an analysis looks for. A model with sub-models says which one is
   *  promoted to take its place (it becomes a root and the others go under it): `actionError` says why when it is refused. */
  const remove = (id: string, promote?: string) =>
    attempt(async () => {
      await api.deleteTemplate(id, promote)
      const parentId = find(id)?.parentId
      templates.value = templates.value.filter((t) => t.id !== id)
      if (parentId) updateChildren(parentId, (children) => children.filter((c) => c.id !== id))
      // A model with sub-models gave its place to one of them, which took the others under it: ask what it is now.
      if (promote) {
        loading = null
        await loadCatalogue()
      }
    })

  /** Goes back to a version of the model: the owner only; `actionError` says why when it is refused. */
  const restoreVersion = (id: string, version: string) =>
    attempt(async () => keep(await api.restoreVersion(id, version)))

  /** The owner of a sub-model makes it a model of its own; its former model stops listing it. */
  const promote = (id: string) =>
    attempt(async () => {
      const parentId = find(id)?.parentId
      keep(await api.promoteTemplate(id))
      if (parentId) updateChildren(parentId, (children) => children.filter((c) => c.id !== id))
    })

  const toggleStar = (id: string) => attempt(async () => keep(await api.putTemplateStar(id)))

  /** Anyone signed in can star an entity, as a model: it says which ones are worth looking for. */
  const toggleEntityStar = (id: string, entityId: string) =>
    attempt(async () => keep(await api.putEntityStar(id, entityId)))

  /** Anyone signed in can star a suggestion, whatever its status, its author and the owner included. */
  const toggleSuggestionStar = (id: string, suggestionId: string) =>
    attempt(async () => keep(await api.putSuggestionStar(id, suggestionId)))

  /** Only the owner edits a template directly. `document`: undefined keeps it, null removes it. */
  const update = async (id: string, fields: TemplateFields, document?: TemplateDocument | null, sharing?: Sharing) =>
    keep(await api.putTemplate(id, toBody(fields, document === undefined ? undefined : (document?.id ?? null), sharing)))

  /** Anyone but the owner can propose a change; it waits for the owner's decision. */
  const suggest = async (id: string, fields: TemplateFields, message: string) =>
    keep(await api.postSuggestion(id, toBody(fields), message))

  /** Anyone signed in can comment a suggestion, whatever its status. */
  const addComment = (id: string, suggestionId: string, text: string) =>
    attempt(async () => keep(await api.postComment(id, suggestionId, text)))

  /** The owner or an administrator decides; accepting applies the proposed fields. */
  const resolveSuggestion = (id: string, suggestionId: string, accept: boolean) =>
    attempt(async () => keep(await api.putDecision(id, suggestionId, accept)))

  return {
    templates,
    failed,
    actionError,
    knownCategories,
    find,
    isOwner,
    canDecide,
    isStarred,
    pendingSuggestions,
    templateName,
    pageLabel,
    filter,
    create,
    remove,
    toggleStar,
    promote,
    restoreVersion,
    toggleEntityStar,
    toggleSuggestionStar,
    addComment,
    update,
    suggest,
    resolveSuggestion,
  }
}
