import { computed, ref } from 'vue'
import {
  analyses as seed,
  sampleLetter,
  type Analysis,
  type AnalysisRun,
  type AnalysisStatus,
  type Detection,
  type Review,
  type ReviewedDetection,
  type Share,
  type TemplateDocument,
  type Zone,
} from '../data/mock'
import { documentError, isImage } from './useCatalogue'
import { useCatalogue } from './useCatalogue'
import { useGroups } from './useGroups'
import { useSession } from './useSession'

// In memory only: a created analysis is lost on reload until the backend exists.
const analyses = ref<Analysis[]>(initialAnalyses())

let sequence = 0
const newId = (prefix: string) => `${prefix}${Date.now()}-${++sequence}`
const today = () => new Date().toISOString().slice(0, 10)

/**
 * The demo data: the uses that name a document get what the analysis found in it, still to be looked at, except for one
 * where the first element is already confirmed and the first run keeps a capture of its document.
 */
function initialAnalyses(): Analysis[] {
  const list = structuredClone(seed)
  for (const analysis of list) {
    for (const run of analysis.runs) {
      if (!run.fileName) continue
      run.detections = simulateTest(analysis, { name: run.fileName, size: 1 }).map((d) => ({ ...d, review: { status: 'pending' as const }, source: 'analysis' as const }))
      run.page = { classifications: simulatePage(analysis, { name: run.fileName, size: 1 }), review: { status: 'pending' } }
      run.screenshot = null
    }
  }
  const first = list.find((a) => a.id === 'a1')!.runs[0]
  first.screenshot = { name: 'courrier-octobre-1.svg', type: 'image/svg+xml', url: sampleLetter }
  if (first.detections?.[0]) first.detections[0].review = { status: 'validated' }
  return list
}

/** Back to the demo data. For the tests, which would otherwise see what the previous one left behind. */
export function resetAnalyses() {
  analyses.value = initialAnalyses()
}

export interface AnalysisStats {
  views: number
  uses: number
  running: number
  failed: number
  done: number
}

/** What a dashboard says of a set of analyses: how often seen and used, and how the uses went. */
export function statsOf(list: Analysis[]): AnalysisStats {
  const runs = list.flatMap((a) => a.runs)
  const count = (status: AnalysisStatus) => runs.filter((r) => r.status === status).length
  return {
    views: list.reduce((total, a) => total + a.views, 0),
    uses: runs.length,
    running: count('running'),
    failed: count('failed'),
    done: count('done'),
  }
}

import type { Classification } from '../data/mock'
export type { Classification, Detection } from '../data/mock'

// A small hash of the name of the file: the same file always gives the same answer, which is what a demo needs.
function hash(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
  return h >>> 0
}

/** A seeded source of numbers between 0 and 1 (mulberry32): the same seed, the same sequence. */
function random(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Every class something could be, the likeliest first, adding up to 100 %: the analysis is 62 to 98 % sure of the best answer,
 * and the rest is shared among the other models of the analysis and « other ».
 */
function classesFor(best: string | null, templateIds: string[], next: () => number): Classification[] {
  const others: (string | null)[] = [...templateIds.filter((t) => t !== best), ...(best === null ? [] : [null])]
  // With no other class to share the rest with, the only one is certain.
  const top = others.length ? 62 + Math.floor(next() * 37) : 100
  const weights = others.map(() => next() + 0.05)
  const total = weights.reduce((sum, w) => sum + w, 0)
  const shares = weights.map((w) => Math.floor(((100 - top) * w) / total))
  if (shares.length) shares[0] += 100 - top - shares.reduce((sum, n) => sum + n, 0) // what rounding left goes to the first
  return [{ templateId: best, confidence: top / 100 }, ...others.map((t, k) => ({ templateId: t, confidence: shares[k] / 100 }))].sort(
    (a, b) => b.confidence - a.confidence,
  )
}

/**
 * Which model the page of a document corresponds to, made up: one of the models of the analysis, with every class it could
 * be. Answers the same for the same file, and differently from what is found in the page.
 */
export function simulatePage(analysis: Pick<Analysis, 'templateIds'>, file: { name: string; size: number }): Classification[] {
  const next = random(hash(`page|${file.name}|${file.size}`))
  const best = analysis.templateIds.length ? analysis.templateIds[Math.floor(next() * analysis.templateIds.length)] : null
  return classesFor(best, analysis.templateIds, next)
}

/**
 * What testing an analysis on a document says, made up: elements found at places of the page, each with what it could be
 * and how sure the analysis is of each. Stands in for the backend, and answers the same for the same file.
 */
export function simulateTest(analysis: Pick<Analysis, 'templateIds'>, file: { name: string; size: number }): Detection[] {
  const next = random(hash(`${file.name}|${file.size}`))
  const found: Omit<Detection, 'id'>[] = []

  for (const templateId of analysis.templateIds) {
    const count = Math.floor(next() * 4) // 0 to 3: a model is missing from a document one time in four
    for (let i = 0; i < count; i++) {
      // A zone: mostly a rectangle, sometimes a polygon with a corner cut, as drawn on a model.
      const w = 0.12 + next() * 0.23
      const h = 0.06 + next() * 0.16
      const x = 0.03 + next() * (0.94 - w)
      const y = 0.03 + next() * (0.94 - h)
      const round = (n: number) => Math.round(n * 1000) / 1000
      const corner = next() < 0.35
      const points = corner
        ? [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h * 0.6 }, { x: x + w * 0.8, y: y + h }, { x, y: y + h }]
        : [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }]

      const classifications = classesFor(templateId, analysis.templateIds, next)
      found.push({ zone: { page: 1, points: points.map((p) => ({ x: round(p.x), y: round(p.y) })) }, classifications })
    }
  }

  // In reading order, top to bottom and left to right.
  const top = (d: Omit<Detection, 'id'>) => Math.min(...d.zone.points.map((p) => p.y))
  const left = (d: Omit<Detection, 'id'>) => Math.min(...d.zone.points.map((p) => p.x))
  return found.sort((a, b) => top(a) - top(b) || left(a) - left(b)).map((d, i) => ({ ...d, id: `d${i + 1}` }))
}

export function useAnalyses() {
  const { userId, isAdmin, email } = useSession()
  const { groups } = useGroups()
  const { find: findTemplate } = useCatalogue()

  const total = computed(() => analyses.value.length)
  const find = (id: string) => analyses.value.find((a) => a.id === id)

  /** The groups of the signed-in user, by name. */
  const myGroups = computed(() =>
    userId.value === null ? [] : groups.value.filter((g) => g.memberIds.includes(userId.value!)).map((g) => g.name),
  )

  /**
   * Who can open an analysis and its dashboard: its owner, anyone when it is public, the people and the groups it is shared
   * with, and an administrator, whatever it is.
   */
  function canAccess(analysis: Analysis): boolean {
    if (userId.value === null) return false
    if (isAdmin.value || analysis.ownerId === userId.value || analysis.isPublic) return true
    return analysis.shares.some((s) =>
      s.kind === 'email' ? s.value.toLowerCase() === email.value : myGroups.value.includes(s.value),
    )
  }

  /** What the signed-in user can open. */
  const accessible = computed(() => analyses.value.filter(canAccess))

  /** One more look at the page of an analysis: counted for whoever can open it, and for no one else. */
  function registerView(id: string): boolean {
    const analysis = find(id)
    if (!analysis || !canAccess(analysis)) return false
    analysis.views++
    return true
  }

  const modelNames = (analysis: Analysis) => analysis.templateIds.map((id) => findTemplate(id)?.name ?? 'Modèle inconnu')

  /** Newest first. An analysis starts with its first use, running, with nothing found yet. */
  function createAnalysis(input: {
    name: string
    description: string
    templateIds: string[]
    isPublic: boolean
    shares: Share[]
  }): Analysis {
    const date = today()
    const run: AnalysisRun = { id: newId('r'), userId: userId.value ?? '', date, status: 'running', matches: 0 }
    const analysis: Analysis = {
      id: newId('a'),
      name: input.name.trim(),
      description: input.description.trim(),
      ownerId: userId.value ?? '',
      views: 0,
      runs: [run],
      templateIds: input.templateIds,
      isPublic: input.isPublic,
      // A public analysis is for everyone: no recipients to keep.
      shares: input.isPublic ? [] : input.shares.map((s) => ({ ...s })),
      date,
      status: 'running',
      matches: 0,
    }
    analyses.value = [analysis, ...analyses.value]
    return analysis
  }

  /** Whether a use is one's own: what it found is for the person who ran it, whoever else can open the analysis. */
  const ownsRun = (run: AnalysisRun) => userId.value !== null && run.userId === userId.value

  /** An administrator included: the results of a use are private to the person who ran it. */
  const canSeeResult = (run: AnalysisRun) => ownsRun(run) && !!run.detections

  const findRun = (analysisId: string, runId: string) => find(analysisId)?.runs.find((r) => r.id === runId)

  /**
   * Tries an analysis on a document, which makes a use of it: done at once, with what was found (still to be looked at),
   * and a capture of the document if asked to keep one. Null for someone who cannot open the analysis, or a document that
   * is not an image or a PDF.
   */
  function startRun(analysisId: string, file: File, options: { saveScreenshot: boolean }): AnalysisRun | null {
    const analysis = find(analysisId)
    if (!analysis || !canAccess(analysis) || documentError(file) || userId.value === null) return null
    // A PDF has nothing to show: its capture would be empty, so none is kept.
    const screenshot: TemplateDocument | null =
      options.saveScreenshot && isImage(file) ? { name: file.name, type: file.type, url: URL.createObjectURL(file) } : null
    const detections = simulateTest(analysis, file).map((d) => ({ ...d, review: { status: 'pending' as const }, source: 'analysis' as const }))
    const run: AnalysisRun = {
      id: newId('r'),
      userId: userId.value,
      date: today(),
      status: 'done',
      matches: detections.length,
      fileName: file.name,
      detections,
      page: { classifications: simulatePage(analysis, file), review: { status: 'pending' } },
      screenshot,
    }
    analysis.runs = [run, ...analysis.runs]
    return analysis.runs[0]
  }

  /**
   * What the person decides of a prediction: right, wrong, or corrected with one of the models of the analysis (and no other
   * model: it is what the analysis looks for). Back to « pending » takes the decision back. Only for one's own results.
   */
  function reviewDetection(analysisId: string, runId: string, detectionId: string, review: Review): boolean {
    const analysis = find(analysisId)
    const run = findRun(analysisId, runId)
    const detection = run?.detections?.find((d) => d.id === detectionId)
    if (!analysis || !run || !detection || !canSeeResult(run)) return false
    if (review.status === 'annotated' && !(review.templateId && analysis.templateIds.includes(review.templateId))) return false
    detection.review = review.status === 'annotated' ? { status: 'annotated', templateId: review.templateId } : { status: review.status }
    return true
  }

  /** What the person decides of the classification of the page: right, wrong, or another of the models of the analysis. */
  function reviewPage(analysisId: string, runId: string, review: Review): boolean {
    const analysis = find(analysisId)
    const run = findRun(analysisId, runId)
    if (!analysis || !run?.page || !canSeeResult(run)) return false
    if (review.status === 'annotated' && !(review.templateId && analysis.templateIds.includes(review.templateId))) return false
    run.page.review = review.status === 'annotated' ? { status: 'annotated', templateId: review.templateId } : { status: review.status }
    return true
  }

  /**
   * Adds by hand an element the analysis missed: a zone drawn on the document, annotated with one of the models of the
   * analysis. It is a decision from the start, so it counts as looked at. Null for anything that is not a zone, or a model
   * that is not one of the analysis.
   */
  function addElement(analysisId: string, runId: string, input: { zone: Zone; templateId: string }): ReviewedDetection | null {
    const analysis = find(analysisId)
    const run = findRun(analysisId, runId)
    if (!analysis || !run?.detections || !canSeeResult(run)) return null
    if (!analysis.templateIds.includes(input.templateId) || input.zone.points.length < 3) return null
    const taken = run.detections.map((d) => Number(d.id.match(/^m(\d+)$/)?.[1] ?? 0))
    const element: ReviewedDetection = {
      id: `m${Math.max(0, ...taken) + 1}`,
      zone: { page: input.zone.page, points: input.zone.points.map((p) => ({ ...p })) },
      classifications: [{ templateId: input.templateId, confidence: 1 }],
      review: { status: 'annotated', templateId: input.templateId },
      source: 'manual',
    }
    run.detections = [...run.detections, element]
    return run.detections[run.detections.length - 1]
  }

  /** Takes away an element that was added by hand. What the analysis found cannot be removed, only rejected. */
  function removeElement(analysisId: string, runId: string, detectionId: string): boolean {
    const run = findRun(analysisId, runId)
    const element = run?.detections?.find((d) => d.id === detectionId)
    if (!run?.detections || !element || element.source !== 'manual' || !canSeeResult(run)) return false
    run.detections = run.detections.filter((d) => d.id !== detectionId)
    return true
  }

  /** How many of the predictions of a use (its elements, and its page) have been looked at. */
  const reviewProgress = (run: AnalysisRun) => {
    const all = [...(run.detections ?? []).map((d) => d.review), ...(run.page ? [run.page.review] : [])]
    return { total: all.length, reviewed: all.filter((r) => r.status !== 'pending').length }
  }

  /** Deletes the capture of the document kept with a use: what was found and decided stays. */
  function deleteScreenshot(analysisId: string, runId: string): boolean {
    const run = findRun(analysisId, runId)
    if (!run?.screenshot || !canSeeResult(run)) return false
    if (run.screenshot.url.startsWith('blob:')) URL.revokeObjectURL(run.screenshot.url)
    run.screenshot = null
    run.fileDecision = 'deleted'
    return true
  }

  /** Says the capture is to be kept, which stops asking. */
  function keepScreenshot(analysisId: string, runId: string): boolean {
    const run = findRun(analysisId, runId)
    if (!run?.screenshot || !canSeeResult(run)) return false
    run.fileDecision = 'kept'
    return true
  }

  return {
    analyses,
    total,
    find,
    findRun,
    myGroups,
    canAccess,
    accessible,
    registerView,
    modelNames,
    createAnalysis,
    ownsRun,
    canSeeResult,
    startRun,
    reviewDetection,
    reviewPage,
    addElement,
    removeElement,
    reviewProgress,
    deleteScreenshot,
    keepScreenshot,
  }
}
