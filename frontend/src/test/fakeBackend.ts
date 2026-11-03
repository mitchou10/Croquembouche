import type { Suggestion, Template, TemplateEntity, TemplateFields } from '../data/mock'
import { entityTypeSeed, templates as seed } from '../data/mock'
import { changedFields, cleanCategories, cleanList, MAX_EXAMPLES } from '../composables/useCatalogue'
import { useSession } from '../composables/useSession'

/**
 * The backend, in memory, for the tests of the pages: it answers the calls of `data/api.ts` as the real one does (who
 * may do what is decided here too, by whoever is signed in), from the demo data. What it must do is tested on the
 * backend's side; this is only what the pages need to be shown working.
 */
interface Answer {
  ok: boolean
  status: number
  json: () => Promise<unknown>
}

interface Stored extends Omit<Template, 'document'> {
  document?: { id: string; name: string; contentType: string; pages: number }
}

let templates: Stored[] = []
// The documents uploaded, by identifier.
const uploads = new Map<string, { id: string; name: string; contentType: string; pages: number }>()
export const uploaded = () => [...uploads.values()]
let sequence = 0
const newId = (prefix: string) => `${prefix}${Date.now()}-${++sequence}`
const today = () => new Date().toISOString().slice(0, 10)

function seedTemplates(): Stored[] {
  return structuredClone(seed).map(({ document, ...rest }) => ({
    ...rest,
    // A demo model's document is an image at an address, with no upload behind it.
    ...(document && { document: { id: `seed-${rest.id}`, name: document.name, contentType: document.type, pages: 1 } }),
  }))
}

export function resetBackend() {
  templates = seedTemplates()
  uploads.clear()
  sequence = 0
}
resetBackend()

const reply = (status: number, body?: unknown): Answer => ({
  ok: status < 400,
  status,
  // A copy, as what comes over the network is: what the pages are given is theirs, not the backend's own.
  json: async () => structuredClone(body),
})
const refuse = (status: number, detail: string) => reply(status, { detail })

interface Body {
  name: string
  description: string
  categories: string[]
  entities: (TemplateEntity & { zone?: TemplateEntity['zone'] | null })[]
  documentId?: string | null
}

function clean(body: Body): TemplateFields {
  return {
    name: body.name.trim(),
    description: body.description.trim(),
    categories: cleanCategories(body.categories),
    entities: body.entities.map((e) => ({
      id: e.id,
      name: e.name.trim(),
      definition: e.definition.trim(),
      type: e.type,
      examples: cleanList(e.examples).slice(0, MAX_EXAMPLES),
      ...(e.zone && { zone: e.zone }),
      stars: [],
    })),
  }
}

/** Entities the model has keep their stars; the others are new, with an identifier of their own. */
function setEntities(template: Stored, entities: TemplateEntity[]) {
  template.entities = entities.map((e) => {
    const current = template.entities.find((c) => c.id === e.id)
    return { ...e, id: current ? current.id : newId('e'), stars: current?.stars ?? [] }
  })
}

const toggle = (list: string[], user: string) => (list.includes(user) ? list.filter((u) => u !== user) : [...list, user])

function documentFor(id: string | null | undefined): Stored['document'] | undefined {
  if (!id) return undefined
  return { id, name: id, contentType: 'image/png', pages: 1 }
}

/** The fake `fetch`. */
export async function fakeFetch(path: string, init: RequestInit = {}): Promise<Answer> {
  const { userId, isAdmin } = useSession()
  const user = userId.value
  if (user === null) return refuse(401, 'Not authenticated')
  const method = init.method ?? 'GET'
  const body: unknown = typeof init.body === 'string' ? JSON.parse(init.body) : {}
  const url = new URL(path, 'http://backend')
  const parts = url.pathname.replace(/^\/api\//, '').split('/')

  if (path === '/api/entity-types') return reply(200, entityTypeSeed)

  if (url.pathname === '/api/documents' && method === 'POST') {
    const file = (init.body as FormData).get('file') as File
    const id = newId('d')
    const document = { id, name: file.name, contentType: file.type, pages: file.type === 'application/pdf' ? 3 : 1 }
    uploads.set(id, document)
    return reply(201, document)
  }
  if (parts[0] === 'documents' && method === 'DELETE') {
    uploads.delete(parts[1])
    return reply(204)
  }

  if (parts[0] !== 'templates') return refuse(404, 'Not found')

  if (parts.length === 1) {
    if (method === 'GET') return reply(200, templates)
    const fields = clean(body as Body)
    const created: Stored = {
      id: newId('t'),
      ownerId: user,
      ownerName: user,
      stars: [],
      suggestions: [],
      ...fields,
      entities: [],
    }
    setEntities(created, fields.entities)
    const document = documentFor((body as Body).documentId)
    if (document) created.document = uploads.get(document.id) ?? document
    templates = [created, ...templates]
    return reply(201, created)
  }

  const template = templates.find((t) => t.id === parts[1])
  if (!template) return refuse(404, 'Not found')
  const owner = template.ownerId === user
  const sub = parts[2]

  if (parts.length === 2 && method === 'GET') return reply(200, template)
  if (parts.length === 2 && method === 'PUT') {
    if (!owner) return refuse(403, 'Seul le propriétaire modifie le modèle.')
    const fields = clean(body as Body)
    Object.assign(template, { name: fields.name, description: fields.description, categories: fields.categories })
    setEntities(template, fields.entities)
    const documentId = (body as Body).documentId
    if (documentId !== undefined) {
      const document = documentFor(documentId)
      if (document) template.document = uploads.get(document.id) ?? document
      else delete template.document
    }
    return reply(200, template)
  }
  if (sub === 'star') {
    template.stars = toggle(template.stars, user)
    return reply(200, template)
  }
  if (sub === 'entities' && parts[4] === 'star') {
    const entity = template.entities.find((e) => e.id === parts[3])
    if (!entity) return refuse(404, 'Not found')
    entity.stars = toggle(entity.stars, user)
    return reply(200, template)
  }
  if (sub !== 'suggestions') return refuse(404, 'Not found')

  if (parts.length === 3) {
    if (owner) return refuse(403, 'Le propriétaire modifie le modèle, il ne le suggère pas.')
    const { fields: sent, message } = body as unknown as { fields: Body; message: string }
    const proposed = clean(sent)
    // What the model is, in the order `clean` gives the fields: the comparison is of values, not of how they were written.
    const current = { ...template, entities: clean(template as unknown as Body).entities }
    if (changedFields(current as unknown as Template, proposed).length === 0) {
      return refuse(422, 'Modifiez au moins un champ pour envoyer une suggestion.')
    }
    const suggestion: Suggestion = {
      id: newId('s'),
      authorId: user,
      authorName: user,
      fields: proposed,
      message: message.trim(),
      date: today(),
      status: 'pending',
      comments: [],
      stars: [],
    }
    template.suggestions = [suggestion, ...template.suggestions]
    return reply(201, template)
  }

  const suggestion = template.suggestions.find((s) => s.id === parts[3])
  if (!suggestion) return refuse(404, 'Not found')
  if (parts[4] === 'star') {
    suggestion.stars = toggle(suggestion.stars, user)
    return reply(200, template)
  }
  if (parts[4] === 'comments') {
    const text = (body as unknown as { text: string }).text.trim()
    if (!text || text.length > 500) return refuse(422, 'Commentaire invalide.')
    suggestion.comments = [
      ...suggestion.comments,
      { id: newId('c'), authorId: user, authorName: user, text, date: today() },
    ]
    return reply(201, template)
  }
  if (parts[4] === 'decision') {
    if (!owner && !isAdmin.value) return refuse(403, 'Seul le propriétaire ou un administrateur décide des suggestions.')
    if (suggestion.status !== 'pending') return refuse(422, 'Cette suggestion a déjà reçu une réponse.')
    const { accept } = body as unknown as { accept: boolean }
    if (accept) {
      Object.assign(template, {
        name: suggestion.fields.name,
        description: suggestion.fields.description,
        categories: suggestion.fields.categories,
      })
      setEntities(template, suggestion.fields.entities)
    }
    suggestion.status = accept ? 'accepted' : 'rejected'
    return reply(200, template)
  }
  return refuse(404, 'Not found')
}
