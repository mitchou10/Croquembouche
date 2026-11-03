import type {
  Analysis,
  AnalysisRun,
  Classification,
  EntityTypeInfo,
  Group,
  Review,
  ReviewedDetection,
  Share,
  Template,
  TemplateDocument,
  Zone,
} from './mock'

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

/** GET /api/groups: the groups an analysis can be shared with, the signed-in user's own. */
export const fetchGroups = () => request<Group[]>('GET', '/api/groups')

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

// ------------------------------------------------------------------------------------------------ analyses

interface ReviewAnswer {
  status: Review['status']
  templateId: string | null
}

interface RunAnswer extends Omit<AnalysisRun, 'fileName' | 'detections' | 'page' | 'screenshot' | 'fileDecision'> {
  fileName: string | null
  detections: (Omit<ReviewedDetection, 'review'> & { review: ReviewAnswer })[] | null
  page: { classifications: Classification[]; review: ReviewAnswer } | null
  screenshot: DocumentAnswer | null
  fileDecision: 'kept' | 'deleted' | null
}

interface AnalysisAnswer extends Omit<Analysis, 'runs'> {
  runs: RunAnswer[]
}

/** The backend says « none » with null: the page, by leaving it out. */
const toReview = ({ status, templateId }: ReviewAnswer): Review => ({ status, ...(templateId && { templateId }) })

function toRun(run: RunAnswer): AnalysisRun {
  const { fileName, detections, page, screenshot, fileDecision, ...rest } = run
  return {
    ...rest,
    ...(fileName && { fileName }),
    ...(detections && { detections: detections.map((d) => ({ ...d, review: toReview(d.review) })) }),
    ...(page && { page: { classifications: page.classifications, review: toReview(page.review) } }),
    screenshot: screenshot ? fromAnswer(screenshot) : null,
    ...(fileDecision && { fileDecision }),
  }
}

const toAnalysis = (analysis: AnalysisAnswer): Analysis => ({ ...analysis, runs: analysis.runs.map(toRun) })

const analyses = '/api/analyses'

export const fetchAnalyses = async () => (await request<AnalysisAnswer[]>('GET', analyses)).map(toAnalysis)
export const fetchAnalysis = async (id: string) => toAnalysis(await request<AnalysisAnswer>('GET', `${analyses}/${id}`))

export interface AnalysisBody {
  name: string
  description: string
  templateIds: string[]
  isPublic: boolean
  shares: Share[]
}
export const postAnalysis = async (body: AnalysisBody) => toAnalysis(await request<AnalysisAnswer>('POST', analyses, body))

/** One more look at the page of an analysis; says how many there are now. */
export const postView = async (id: string) => (await request<{ views: number }>('POST', `${analyses}/${id}/views`)).views

/** Tries the analysis on a document, which makes a use of it. */
export async function postRun(id: string, file: File, keepScreenshot: boolean): Promise<AnalysisRun> {
  const form = new FormData()
  form.append('file', file)
  form.append('keepScreenshot', String(keepScreenshot))
  return toRun(await request<RunAnswer>('POST', `${analyses}/${id}/runs`, form))
}

const runCall = async (method: string, id: string, runId: string, path: string, body?: unknown) =>
  toRun(await request<RunAnswer>(method, `${analyses}/${id}/runs/${runId}${path}`, body))

const reviewBody = (review: Review) => ({ status: review.status, ...(review.templateId && { templateId: review.templateId }) })

export const putDetectionReview = (id: string, runId: string, detectionId: string, review: Review) =>
  runCall('PUT', id, runId, `/detections/${detectionId}/review`, reviewBody(review))
export const putPageReview = (id: string, runId: string, review: Review) =>
  runCall('PUT', id, runId, '/page/review', reviewBody(review))
export const postElement = (id: string, runId: string, element: { zone: Zone; templateId: string }) =>
  runCall('POST', id, runId, '/elements', element)
export const deleteElement = (id: string, runId: string, detectionId: string) =>
  runCall('DELETE', id, runId, `/elements/${detectionId}`)
export const putFileDecision = (id: string, runId: string, decision: 'kept' | 'deleted') =>
  runCall('PUT', id, runId, '/file', { decision })
