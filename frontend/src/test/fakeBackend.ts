import type {
  Analysis,
  AnalysisRun,
  Review,
  ReviewedDetection,
  PageFields,
  Share,
  Suggestion,
  Template,
  TemplateEntity,
  TemplateFields,
  TemplateQuality,
  QualityOverview,
} from '../data/mock'
import { analyses as analysisSeed, entityTypeSeed, groupSeed, sampleLetter, templates as seed } from '../data/mock'
import { simulatePage, simulateTest } from './simulate'
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

/** The versions each model has had, newest first: only the ones a test looked at or went back to. */
const history = new Map<string, unknown[]>()
const versionOf = (template: Stored) => ({
  version: template.version,
  date: '2026-11-04',
  authorId: template.ownerId,
  authorName: template.ownerId,
  document: template.document ?? null,
})

/** How many pages the document of a model has: 0 when it has none. */
const pagesOfDocument = (template: Stored) => template.document?.pages ?? 0
const labelOf = (name: string, total: number, page: number, given = '') =>
  given ? `${name} · ${given}` : total > 1 ? `${name} · page ${page}` : name

/** The pages of a model: one per page of its document, with what was said of them and how each is called. */
function buildPages(template: Stored, given: PageFields[]): void {
  const total = pagesOfDocument(template)
  template.pages = Array.from({ length: total }, (_, i) => {
    const note = given.find((g) => g.page === i + 1)
    const name = note?.name.trim() ?? ''
    return { page: i + 1, name, description: note?.description.trim() ?? '', label: labelOf(template.name, total, i + 1, name) }
  })
}
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

let analyses: Analysis[] = []
/** An analysis as the backend itself holds it, for the tests to look at what the pages did to it. */
export const backendAnalysis = (id: string) => analyses.find((a) => a.id === id)!

/**
 * The demo analyses: the uses that name a document get what the analysis found in it, still to be looked at, except for
 * one where the first element is already confirmed and the first run keeps a capture of its document.
 */
function seedAnalyses(): Analysis[] {
  const list = structuredClone(analysisSeed)
  for (const analysis of list) {
    for (const run of analysis.runs) {
      if (!run.fileName) continue
      run.detections = simulateTest(analysis, { name: run.fileName, size: 1 }).map((d) => ({
        ...d,
        review: { status: 'pending' as const },
        source: 'analysis' as const,
      }))
      run.pages = [{ page: 1, classifications: simulatePage(analysis, { name: run.fileName, size: 1 }, 1, pagesOfModel), review: { status: 'pending' } }]
      run.screenshot = null
    }
  }
  const first = list.find((a) => a.id === 'a1')!.runs[0]
  first.screenshot = { id: 'seed-shot', name: 'courrier-octobre-1.svg', type: 'image/svg+xml', url: sampleLetter, pages: 1 }
  if (first.detections?.[0]) first.detections[0].review = { status: 'validated' }
  return list
}

export function resetBackend() {
  templates = seedTemplates()
  analyses = seedAnalyses()
  uploads.clear()
  history.clear()
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
  parentId?: string
  pages?: PageFields[]
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
    pages: (body.pages ?? []).filter((p) => p.name.trim() || p.description.trim()),
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
  if (parts[0] === 'documents' && parts[2] === 'suggestions') {
    // What a PDF suggests: two fields, on two pages. An image suggests nothing.
    const document = uploads.get(parts[1])
    if (!document) return refuse(404, 'Not found')
    const square = (page: number) => ({ page, points: [{ x: 0.1, y: 0.1 }, { x: 0.5, y: 0.1 }, { x: 0.5, y: 0.2 }, { x: 0.1, y: 0.2 }] })
    return reply(
      200,
      document.contentType === 'application/pdf'
        ? [
            { name: 'Nom du demandeur', type: 'text', zone: square(1), source: 'widget' },
            { name: 'Date de naissance', type: 'date', zone: square(2), source: 'box' },
          ]
        : [],
    )
  }
  if (parts[0] === 'documents' && method === 'DELETE') {
    uploads.delete(parts[1])
    return reply(204)
  }

  if (parts[0] === 'groups') return reply(200, groupsOf(user))
  if (parts[0] === 'metrics') {
    if (parts[1] === 'me') return reply(200, overviewOf(user))
    return isAdmin.value ? reply(200, overviewOf()) : refuse(403, 'Réservé aux administrateurs.')
  }
  if (parts[0] === 'analyses') return analysesRoute(user, isAdmin.value, method, parts, body, init)

  if (parts[0] !== 'templates') return refuse(404, 'Not found')

  if (parts.length === 1) {
    if (method === 'GET') return reply(200, templates)
    const fields = clean(body as Body)
    const parentId = (body as Body).parentId
    const parent = parentId ? templates.find((t) => t.id === parentId) : undefined
    if (parentId && !parent) return refuse(422, 'Le modèle parent n’existe pas.')
    if (parent?.parentId) return refuse(422, 'Un sous-modèle ne peut pas avoir de sous-modèle.')
    if (parent && parent.ownerId !== user) return refuse(403, 'Seul le propriétaire du modèle lui ajoute un sous-modèle.')
    const created: Stored = {
      id: newId('t'),
      version: '1.0.0',
      parentId: parent?.id ?? null,
      parentName: parent?.name ?? null,
      children: [],
      ownerId: user,
      ownerName: user,
      stars: [],
      suggestions: [],
      ...fields,
      pages: [],
      entities: [],
    }
    setEntities(created, fields.entities)
    const document = documentFor((body as Body).documentId)
    if (document) created.document = uploads.get(document.id) ?? document
    buildPages(created, fields.pages)
    templates = [created, ...templates]
    parent?.children.push({ id: created.id, name: created.name, version: created.version })
    return reply(201, created)
  }

  const template = templates.find((t) => t.id === parts[1])
  if (!template) return refuse(404, 'Not found')
  const owner = template.ownerId === user
  const sub = parts[2]

  if (parts.length === 2 && method === 'GET') return reply(200, template)
  if (parts.length === 3 && parts[2] === 'metrics' && method === 'GET') return reply(200, qualityOf(template))
  if (parts[2] === 'versions') {
    // The history starts with the version the model is at; going back adds a new one on top.
    const kept = (history.get(template.id) ?? [versionOf(template)]) as ReturnType<typeof versionOf>[]
    history.set(template.id, kept)
    if (parts.length === 3 && method === 'GET') return reply(200, kept)
    if (parts.length === 5 && parts[4] === 'restore' && method === 'POST') {
      if (!owner) return refuse(403, 'Seul le propriétaire modifie le modèle.')
      if (!kept.some((v) => v.version === parts[3])) return refuse(404, 'Not found')
      const [major, minor] = template.version.split('.').map(Number)
      template.version = `${major}.${minor + 1}.0`
      history.set(template.id, [versionOf(template), ...kept])
      return reply(200, template)
    }
    return refuse(404, 'Not found')
  }
  if (parts.length === 2 && method === 'DELETE') {
    if (!owner) return refuse(403, 'Seul le propriétaire supprime le modèle.')
    const used = analyses.filter((a) => a.templateIds.includes(template.id)).length
    if (used) return refuse(409, `Ce modèle est utilisé par ${used} analyse${used > 1 ? 's' : ''} : supprimez-la${used > 1 ? 's' : ''} d’abord.`)
    if (template.children.length) {
      const promote = url.searchParams.get('promote')
      if (!promote) return refuse(409, 'Ce modèle a des sous-modèles : choisissez celui qui prend sa place.')
      const chosen = templates.find((t) => t.id === promote && t.parentId === template.id)
      if (!chosen) return refuse(422, 'Choisissez un des sous-modèles de ce modèle.')
      // It becomes a root, and the others go under it.
      const others = template.children.filter((c) => c.id !== chosen.id)
      chosen.parentId = null
      chosen.parentName = null
      chosen.children = others
      for (const other of others) {
        const child = templates.find((t) => t.id === other.id)
        if (child) Object.assign(child, { parentId: chosen.id, parentName: chosen.name })
      }
    }
    templates = templates.filter((t) => t.id !== template.id)
    const parent = templates.find((t) => t.id === template.parentId)
    if (parent) parent.children = parent.children.filter((c) => c.id !== template.id)
    return reply(204)
  }
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
    buildPages(template, fields.pages)
    return reply(200, template)
  }
  if (sub === 'promote' && method === 'POST') {
    if (!owner) return refuse(403, 'Seul le propriétaire promeut le modèle.')
    if (!template.parentId) return refuse(422, 'Ce modèle n’est pas un sous-modèle.')
    const parent = templates.find((t) => t.id === template.parentId)
    if (parent) parent.children = parent.children.filter((c) => c.id !== template.id)
    template.parentId = null
    template.parentName = null
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
      buildPages(template, suggestion.fields.pages)
    }
    suggestion.status = accept ? 'accepted' : 'rejected'
    return reply(200, template)
  }
  return refuse(404, 'Not found')
}

// ------------------------------------------------------------------------------------------------ analyses

const emailOf = (user: string) => `${user.toLowerCase()}@example.org`
const groupsOf = (user: string) => groupSeed.filter((g) => g.memberIds.includes(user))

function canOpen(analysis: Analysis, user: string, admin: boolean): boolean {
  if (admin || analysis.ownerId === user || analysis.isPublic) return true
  const groups = groupsOf(user).map((g) => g.name)
  return analysis.shares.some((s) => (s.kind === 'email' ? s.value.toLowerCase() === emailOf(user) : groups.includes(s.value)))
}

// The uses the worker has not answered yet, with how it answers, and how many times each was asked for.
const answers = new Map<string, () => void>()
const asked = new Map<string, number>()

function answer(run: AnalysisRun, analysis: Analysis, detections: ReviewedDetection[], pages: NonNullable<AnalysisRun['pages']>, broken: boolean) {
  answers.delete(run.id)
  if (broken) {
    run.status = 'failed'
    return
  }
  run.status = 'done'
  run.matches = detections.length
  run.detections = detections
  run.pages = pages
  analysis.matches += run.matches
}

/** One prediction and what was decided of it, as the metrics see it. */
interface Row {
  top: string | null
  confidence: number
  review: Review
  manual?: boolean
  entityId?: string | null
}

interface Collected {
  pages: Row[]
  elements: Row[]
}

/** The predictions of the uses (of one person, when named) and what was decided of them. */
function collect(user?: string): Collected {
  const pages: Row[] = []
  const elements: Row[] = []
  for (const run of analyses.flatMap((a) => a.runs).filter((r) => user === undefined || r.userId === user)) {
    for (const page of run.pages ?? []) {
      const top = [...page.classifications].sort((a, b) => b.confidence - a.confidence)[0]
      pages.push({ top: top?.templateId ?? null, confidence: top?.confidence ?? 0, review: page.review })
    }
    for (const d of run.detections ?? []) {
      // An element found is the claim that there is one: the model it is taken for is the likeliest model, « other » or not.
      const top = [...d.classifications].filter((c) => c.templateId).sort((a, b) => b.confidence - a.confidence)[0]
      elements.push({ top: top?.templateId ?? null, confidence: top?.confidence ?? 0, review: d.review, manual: d.source === 'manual', entityId: d.entityId })
    }
  }
  return { pages, elements }
}

/** What was predicted as the model (as any, when none is named) and what was decided of it (the backend's rules). */
function quality(rows: Row[], model?: string) {
  const predictedAs = (r: Row) => !r.manual && r.top !== null && (model === undefined || r.top === model)
  const predicted = rows.filter(predictedAs)
  const decided = predicted.filter((r) => r.review.status !== 'pending')
  const right = (r: Row) => r.review.status === 'validated' || (r.review.status === 'annotated' && r.review.templateId === (model ?? r.top))
  const correct = decided.filter(right)
  const wrong = decided.filter((r) => !right(r))
  const missed = rows.filter(
    (r) =>
      r.review.status === 'annotated' &&
      !!r.review.templateId &&
      (model === undefined || r.review.templateId === model) &&
      !(predictedAs(r) && r.top === r.review.templateId),
  )
  const ratio = (a: number, b: number) => (b ? Math.round((a / b) * 10000) / 10000 : null)
  const mean = (list: Row[]) => (list.length ? Math.round((list.reduce((s, r) => s + r.confidence, 0) / list.length) * 10000) / 10000 : null)
  const precision = ratio(correct.length, decided.length)
  const recall = ratio(correct.length, correct.length + missed.length)
  return {
    reviewed: decided.length,
    pending: predicted.length - decided.length,
    correct: correct.length,
    wrong: wrong.length,
    missed: missed.length,
    precision,
    recall,
    f1: precision && recall ? Math.round(((2 * precision * recall) / (precision + recall)) * 10000) / 10000 : null,
    meanConfidenceCorrect: mean(correct),
    meanConfidenceWrong: mean(wrong),
  }
}

/** The quality of the analysis on a model, from the decisions in every use. */
function qualityOf(template: Pick<Template, 'id' | 'entities'>): TemplateQuality {
  const { pages, elements } = collect()
  return {
    pages: { ...quality(pages, template.id), exact: null },
    elements: quality(elements, template.id),
    entities: template.entities.map((e) => ({ id: e.id, name: e.name, ...quality(elements.filter((r) => r.entityId === e.id), template.id) })),
  }
}

/** The quality over every model, and model by model, of the decisions of one person or of everyone. */
function overviewOf(user?: string): QualityOverview {
  const { pages, elements } = collect(user)
  const ids = new Set<string>()
  for (const r of [...pages, ...elements]) for (const id of [r.top, r.review.templateId]) if (id) ids.add(id)
  const models = [...ids]
    .map((id) => ({
      id,
      name: templates.find((t) => t.id === id)?.name ?? 'Modèle supprimé',
      pages: { ...quality(pages, id), exact: null },
      elements: quality(elements, id),
    }))
    .sort((a, b) => b.pages.reviewed + b.elements.reviewed - (a.pages.reviewed + a.elements.reviewed) || a.name.localeCompare(b.name))
  const reviewers = new Set(
    analyses.flatMap((a) => a.runs).filter((r) => [...(r.pages ?? []).map((p) => p.review), ...(r.detections ?? []).map((d) => d.review)].some((v) => v.status !== 'pending')).map((r) => r.userId),
  )
  return {
    pages: { ...quality(pages), exact: null },
    elements: quality(elements),
    models,
    ...(user === undefined && { reviewers: reviewers.size }),
  }
}

/** What the backend sends of a use: what it found is for the person who ran it alone. */
function runView(run: AnalysisRun, user: string) {
  const mine = run.userId === user
  const { screenshot, detections, pages, fileName, fileDecision, ...rest } = run
  return {
    ...rest,
    hasResult: !!fileName,
    fileName: mine ? (fileName ?? null) : null,
    detections: mine ? (detections ?? null) : null,
    pages: mine ? (pages ?? null) : null,
    screenshot:
      mine && screenshot
        ? { id: screenshot.id ?? 'shot', name: screenshot.name, contentType: screenshot.type, pages: screenshot.pages ?? 1 }
        : null,
    fileDecision: mine ? (fileDecision ?? null) : null,
  }
}

function analysisView(analysis: Analysis, user: string, admin: boolean) {
  if (!canOpen(analysis, user, admin)) {
    return { id: analysis.id, canOpen: false, name: analysis.name, description: '', ownerId: '', ownerName: '', views: 0, runs: [], templateIds: [], isPublic: false, shares: [], date: analysis.date, status: analysis.status, matches: 0 }
  }
  const sees = analysis.ownerId === user || admin
  return { ...analysis, shares: sees ? analysis.shares : [], runs: analysis.runs.map((r) => runView(r, user)) }
}

/** How many pages a model's document has, 0 when it has none: what a page of a document can be classified as. */
function pagesOfModel(templateId: string): number {
  const template = templates.find((t) => t.id === templateId)
  return template ? pagesOfDocument(template) : 0
}

/** A PDF tried has three pages here, an image one. */
function pagesInFile(file: File): number {
  return file.type === 'application/pdf' ? 3 : 1
}

const sameShare = (a: Share, b: Share) => a.kind === b.kind && a.value.toLowerCase() === b.value.toLowerCase()

function checkReview(analysis: Analysis, review: Review): string | null {
  if (review.status === 'annotated' && !(review.templateId && analysis.templateIds.includes(review.templateId))) {
    return 'Choisissez un des modèles de l’analyse.'
  }
  return null
}

const asReview = (review: Review): Review =>
  review.status === 'annotated' ? { status: 'annotated', templateId: review.templateId } : { status: review.status }

function analysesRoute(user: string, admin: boolean, method: string, parts: string[], body: unknown, init: RequestInit): Answer {
  if (parts.length === 1) {
    if (method === 'GET') return reply(200, analyses.map((a) => analysisView(a, user, admin)))
    const input = body as { name: string; description: string; templateIds: string[]; isPublic: boolean; shares: Share[] }
    if (!input.name.trim()) return refuse(422, 'Donnez un nom à l’analyse.')
    const date = today()
    const created: Analysis = {
      id: newId('a'),
      canOpen: true,
      name: input.name.trim(),
      description: input.description.trim(),
      ownerId: user,
      ownerName: user,
      views: 0,
      runs: [{ id: newId('r'), userId: user, userName: user, hasResult: false, date, status: 'running', matches: 0 }],
      templateIds: input.templateIds,
      isPublic: input.isPublic,
      // A public analysis is for everyone: no recipients to keep.
      shares: input.isPublic ? [] : input.shares.filter((s, i, all) => all.findIndex((o) => sameShare(o, s)) === i),
      date,
      status: 'running',
      matches: 0,
    }
    analyses = [created, ...analyses]
    return reply(201, analysisView(created, user, admin))
  }

  const analysis = analyses.find((a) => a.id === parts[1])
  if (!analysis || !canOpen(analysis, user, admin)) return refuse(404, 'Not found')
  if (parts.length === 2 && method === 'DELETE') {
    if (analysis.ownerId !== user) return refuse(403, 'Seul le propriétaire supprime l’analyse.')
    analyses = analyses.filter((a) => a.id !== analysis.id)
    return reply(204)
  }
  if (parts.length === 2) return reply(200, analysisView(analysis, user, admin))
  if (parts[2] === 'views') {
    analysis.views++
    return reply(200, { views: analysis.views })
  }
  if (parts[2] !== 'runs') return refuse(404, 'Not found')

  if (parts.length === 3) {
    const file = (init.body as FormData).get('file') as File
    const keep = (init.body as FormData).get('keepScreenshot') === 'true'
    if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'application/pdf'].includes(file.type)) {
      return refuse(422, 'Seuls les images (PNG, JPEG, WebP, GIF) et les PDF sont acceptés.')
    }
    const detections: ReviewedDetection[] = simulateTest(analysis, file).map((d) => ({
      ...d,
      review: { status: 'pending' as const },
      source: 'analysis' as const,
    }))
    const pages = Array.from({ length: pagesInFile(file) }, (_, i) => ({
      page: i + 1,
      classifications: simulatePage(analysis, file, i + 1, pagesOfModel),
      review: { status: 'pending' as const },
    }))
    // A file whose name says « slow » is answered by the worker later, as the real one is: running, then done (or failed
    // when it says « broken »), at the second time it is asked for.
    const later = /slow|broken/.test(file.name)
    const run: AnalysisRun = {
      id: newId('r'),
      userId: user,
      userName: user,
      hasResult: true,
      date: today(),
      status: later ? 'running' : 'done',
      matches: later ? 0 : detections.length,
      fileName: file.name,
      detections: later ? [] : detections,
      pages: later ? undefined : pages,
      screenshot: keep ? { id: newId('d'), name: file.name, type: file.type, url: '', pages: file.type === 'application/pdf' ? 3 : 1 } : null,
    }
    analysis.runs = [run, ...analysis.runs]
    analysis.matches += run.matches
    if (later) answers.set(run.id, () => answer(run, analysis, detections, pages, file.name.includes('broken')))
    return reply(201, runView(run, user))
  }

  const run = analysis.runs.find((r) => r.id === parts[3])
  // What a use found is its person's alone, an administrator included.
  if (!run || run.userId !== user) return refuse(404, 'Not found')
  if (parts.length === 4) {
    // The worker answers the second time the use is asked for.
    const seen = (asked.get(run.id) ?? 0) + 1
    asked.set(run.id, seen)
    if (seen >= 2) answers.get(run.id)?.()
    return reply(200, runView(run, user))
  }
  if (parts[4] === 'cancel' && method === 'POST') {
    if (run.status === 'running') {
      run.status = 'cancelled'
      answers.delete(run.id)
    }
    return reply(200, runView(run, user))
  }
  const detection = run.detections?.find((d) => d.id === parts[5])

  if (parts[4] === 'detections' && parts[6] === 'review') {
    if (!detection) return refuse(404, 'Not found')
    const review = body as Review
    const fault = checkReview(analysis, review)
    if (fault) return refuse(422, fault)
    detection.review = asReview(review)
    return reply(200, runView(run, user))
  }
  if (parts[4] === 'pages' && parts[6] === 'review') {
    const decided = run.pages?.find((p) => p.page === Number(parts[5]))
    if (!decided) return refuse(404, 'Not found')
    const review = body as Review
    const fault = checkReview(analysis, review)
    if (fault) return refuse(422, fault)
    if (review.status === 'annotated') {
      const total = pagesOfModel(review.templateId!)
      if (total > 1 && !review.templatePage) return refuse(422, 'Choisissez la page du modèle.')
      if (review.templatePage && review.templatePage > Math.max(total, 1)) return refuse(422, 'Ce modèle n’a pas cette page.')
    }
    decided.review = { ...asReview(review), ...(review.status === 'annotated' && review.templatePage && { templatePage: review.templatePage }) }
    return reply(200, runView(run, user))
  }
  if (parts[4] === 'elements' && parts.length === 5 && method === 'POST') {
    const { zone, templateId, entityId } = body as {
      zone: { page: number; points: { x: number; y: number }[] }
      templateId: string
      entityId?: string
    }
    if (!run.detections) return refuse(404, 'Not found')
    if (!analysis.templateIds.includes(templateId)) return refuse(422, 'Choisissez un des modèles de l’analyse.')
    if (entityId && !templates.find((t) => t.id === templateId)?.entities.some((e) => e.id === entityId)) {
      return refuse(422, 'Choisissez une entité du modèle.')
    }
    if (zone.points.length < 3) return refuse(422, 'Zone invalide.')
    const taken = run.detections.map((d) => Number(d.id.match(/^m(\d+)$/)?.[1] ?? 0))
    run.detections = [
      ...run.detections,
      {
        id: `m${Math.max(0, ...taken) + 1}`,
        zone,
        classifications: [{ templateId, confidence: 1 }],
        review: { status: 'annotated', templateId },
        source: 'manual',
        ...(entityId && { entityId }),
      },
    ]
    return reply(201, runView(run, user))
  }
  if (parts[4] === 'elements' && method === 'DELETE') {
    if (!detection) return refuse(404, 'Not found')
    if (detection.source !== 'manual') return refuse(422, 'Ce qu’a trouvé l’analyse ne s’efface pas : refusez-le.')
    run.detections = run.detections!.filter((d) => d.id !== detection.id)
    return reply(200, runView(run, user))
  }
  if (parts[4] === 'file') {
    if (!run.screenshot) return refuse(404, 'Not found')
    const { decision } = body as { decision: 'kept' | 'deleted' }
    if (decision === 'deleted') run.screenshot = null
    run.fileDecision = decision
    return reply(200, runView(run, user))
  }
  return refuse(404, 'Not found')
}
