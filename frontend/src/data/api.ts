import { groupSeed, type EntityTypeInfo, type Group, type Template, type TemplateDocument } from './mock'

/** What the backend refuses, with the reason it gives (in French, to show as is). */
export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, credentials: 'same-origin' }
  if (body instanceof FormData) init.body = body
  else if (body !== undefined) {
    init.body = JSON.stringify(body)
    init.headers = { 'Content-Type': 'application/json' }
  }
  const response = await fetch(path, init)
  if (!response.ok) {
    let detail = ''
    try {
      const payload = await response.json()
      // A refusal of the backend says why in `detail`; a malformed request gives a list of faults instead.
      detail = typeof payload.detail === 'string' ? payload.detail : ''
    } catch {
      // No explanation to give.
    }
    throw new ApiError(detail || 'Le serveur n’a pas pu traiter la demande.', response.status)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

/** GET /api/entity-types */
export const fetchEntityTypes = () => request<EntityTypeInfo[]>('GET', '/api/entity-types')

/** GET /api/groups: the groups an analysis can be shared with. Still the demo data: the backend has no groups yet. */
export async function fetchGroups(): Promise<Group[]> {
  await Promise.resolve()
  return structuredClone(groupSeed)
}

/** What a model is made of, as the backend takes it: the entities keep their id when they already exist. */
export interface TemplateBody {
  name: string
  description: string
  categories: string[]
  entities: {
    id?: string
    name: string
    definition: string
    type: string
    examples: string[]
    zone?: { page: number; points: { x: number; y: number }[] }
  }[]
  /** Absent keeps the document; null removes it. */
  documentId?: string | null
}

interface DocumentAnswer {
  id: string
  name: string
  contentType: string
  pages: number
}

/** A template as the backend sends it: no zone is `null`, and the document is the one it has uploaded. */
type TemplateAnswer = Omit<Template, 'document'> & { document: DocumentAnswer | null }

/** The backend says « no zone » with null and « no document » with null: the page says it by leaving it out. */
function toTemplate({ document, ...template }: TemplateAnswer): Template {
  const withoutNullZones = <T extends { zone?: unknown }>(entities: T[]) =>
    entities.map((entity) => {
      if (entity.zone === null) delete entity.zone
      return entity
    })
  withoutNullZones(template.entities)
  for (const suggestion of template.suggestions) withoutNullZones(suggestion.fields.entities)
  return { ...template, ...(document && { document: fromAnswer(document) }) }
}

const base = '/api/templates'
const call = async (method: string, path: string, body?: unknown) =>
  toTemplate(await request<TemplateAnswer>(method, path, body))

export const fetchTemplates = async () => (await request<TemplateAnswer[]>('GET', base)).map(toTemplate)
export const postTemplate = (body: TemplateBody) => call('POST', base, body)
export const putTemplate = (id: string, body: TemplateBody) => call('PUT', `${base}/${id}`, body)
export const putTemplateStar = (id: string) => call('PUT', `${base}/${id}/star`)
export const putEntityStar = (id: string, entityId: string) => call('PUT', `${base}/${id}/entities/${entityId}/star`)
export const postSuggestion = (id: string, fields: TemplateBody, message: string) =>
  call('POST', `${base}/${id}/suggestions`, { fields, message })
export const putDecision = (id: string, suggestionId: string, accept: boolean) =>
  call('PUT', `${base}/${id}/suggestions/${suggestionId}/decision`, { accept })
export const putSuggestionStar = (id: string, suggestionId: string) =>
  call('PUT', `${base}/${id}/suggestions/${suggestionId}/star`)
export const postComment = (id: string, suggestionId: string, text: string) =>
  call('POST', `${base}/${id}/suggestions/${suggestionId}/comments`, { text })

/** The address of the image of a page (from 1) of an uploaded document. */
export const pageUrl = (id: string, page: number) => `/api/documents/${id}/pages/${page}`

/** POST /api/documents: keeps an image or a PDF (for a PDF, a screenshot of each page). */
export async function uploadDocument(file: File): Promise<TemplateDocument> {
  const form = new FormData()
  form.append('file', file)
  const document = await request<DocumentAnswer>('POST', '/api/documents', form)
  return fromAnswer(document)
}

export const fromAnswer = (document: DocumentAnswer): TemplateDocument => ({
  id: document.id,
  name: document.name,
  type: document.contentType,
  pages: document.pages,
  url: pageUrl(document.id, 1),
})

export const deleteDocument = (id: string) => request<void>('DELETE', `/api/documents/${id}`)
