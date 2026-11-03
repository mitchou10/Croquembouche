import { computed, ref } from 'vue'
import * as api from '../data/api'
import type { Analysis, AnalysisRun, AnalysisStatus, Review, Share, Zone } from '../data/mock'
import { useCatalogue } from './useCatalogue'
import { useSession } from './useSession'

// The analyses as the backend has them: every one, those the person cannot open named only. Loaded once, then kept up to
// date with what its answers say.
const analyses = ref<Analysis[]>([])
const failed = ref(false)
let loading: Promise<void> | null = null

export function loadAnalyses(): Promise<void> {
  loading ??= api
    .fetchAnalyses()
    .then((list) => {
      analyses.value = list
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
export function resetAnalyses() {
  analyses.value = []
  failed.value = false
  actionError.value = ''
  loading = null
}

// What the last action was refused for, to show on the page; cleared by the next.
const actionError = ref('')

/** Runs an action whose refusal is shown on the page; says whether it went through. */
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

export type { Classification, Detection } from '../data/mock'

export function useAnalyses() {
  const { userId } = useSession()
  const { find: findTemplate } = useCatalogue()
  void loadAnalyses()

  const total = computed(() => analyses.value.length)
  const find = (id: string) => analyses.value.find((a) => a.id === id)

  /** Whether the analysis can be opened: the backend says (its owner, public, shared with, an administrator). */
  const canAccess = (analysis: Analysis) => analysis.canOpen

  /** What the signed-in user can open. */
  const accessible = computed(() => analyses.value.filter(canAccess))

  /** Puts what the backend answered in the list, where the analysis was or at the top when it is new. */
  function keep(analysis: Analysis): Analysis {
    const index = analyses.value.findIndex((a) => a.id === analysis.id)
    if (index === -1) analyses.value = [analysis, ...analyses.value]
    else analyses.value = analyses.value.map((a, i) => (i === index ? analysis : a))
    return analysis
  }

  /** Puts a use in its analysis, where it was or at the top when it is new. */
  function keepRun(analysisId: string, run: AnalysisRun) {
    const analysis = find(analysisId)
    if (!analysis) return
    const exists = analysis.runs.some((r) => r.id === run.id)
    const runs = exists ? analysis.runs.map((r) => (r.id === run.id ? run : r)) : [run, ...analysis.runs]
    keep({ ...analysis, runs })
  }

  /** One more look at the page of an analysis: counted for whoever can open it, and for no one else. */
  const registerView = (id: string) =>
    attempt(async () => {
      const views = await api.postView(id)
      const analysis = find(id)
      if (analysis) keep({ ...analysis, views })
    })

  const modelNames = (analysis: Pick<Analysis, 'templateIds'>) =>
    analysis.templateIds.map((id) => findTemplate(id)?.name ?? 'Modèle inconnu')

  /** Newest first. An analysis starts with its first use, running, with nothing found yet. Throws an `ApiError`. */
  async function createAnalysis(input: {
    name: string
    description: string
    templateIds: string[]
    isPublic: boolean
    shares: Share[]
  }): Promise<Analysis> {
    return keep(await api.postAnalysis(input))
  }

  /** Only the owner deletes an analysis, with its uses: `actionError` says why when it is refused. */
  const remove = (id: string) =>
    attempt(async () => {
      await api.deleteAnalysis(id)
      analyses.value = analyses.value.filter((a) => a.id !== id)
    })

  /** Whether a use is one's own: what it found is for the person who ran it, whoever else can open the analysis. */
  const ownsRun = (run: AnalysisRun) => userId.value !== null && run.userId === userId.value

  /** An administrator included: the results of a use are private to the person who ran it. */
  const canSeeResult = (run: AnalysisRun) => ownsRun(run) && !!run.detections

  const findRun = (analysisId: string, runId: string) => find(analysisId)?.runs.find((r) => r.id === runId)

  /**
   * Tries an analysis on a document, which makes a use of it: done at once, with what was found (still to be looked at),
   * and the screenshots of the document if asked to keep them. Null when the backend refuses, and `actionError` says why.
   */
  async function startRun(analysisId: string, file: File, options: { saveScreenshot: boolean }): Promise<AnalysisRun | null> {
    let started: AnalysisRun | null = null
    const done = await attempt(async () => {
      started = await api.postRun(analysisId, file, options.saveScreenshot)
      keepRun(analysisId, started)
      // What the analysis counts of its uses has changed.
      keep(await api.fetchAnalysis(analysisId))
    })
    return done ? started : null
  }

  /**
   * What the person decides of a prediction: right, wrong, or corrected with one of the models of the analysis (and no other
   * model: it is what the analysis looks for). Back to « pending » takes the decision back. Only for one's own results.
   */
  const reviewDetection = (analysisId: string, runId: string, detectionId: string, review: Review) =>
    attempt(async () => keepRun(analysisId, await api.putDetectionReview(analysisId, runId, detectionId, review)))

  /**
   * What the person decides of the classification of one page of the document (from 1): right, wrong, or another page
   * of another of the models of the analysis.
   */
  const reviewPage = (analysisId: string, runId: string, page: number, review: Review) =>
    attempt(async () => keepRun(analysisId, await api.putPageReview(analysisId, runId, page, review)))

  /**
   * Adds by hand an element the analysis missed: a zone drawn on the document, annotated with one of the models of the
   * analysis. It is a decision from the start, so it counts as looked at.
   */
  const addElement = (analysisId: string, runId: string, input: { zone: Zone; templateId: string }) =>
    attempt(async () => keepRun(analysisId, await api.postElement(analysisId, runId, input)))

  /** Takes away an element that was added by hand. What the analysis found cannot be removed, only rejected. */
  const removeElement = (analysisId: string, runId: string, detectionId: string) =>
    attempt(async () => keepRun(analysisId, await api.deleteElement(analysisId, runId, detectionId)))

  /** How many of the predictions of a use (its elements, and each of its pages) have been looked at. */
  const reviewProgress = (run: AnalysisRun) => {
    const all = [...(run.detections ?? []).map((d) => d.review), ...(run.pages ?? []).map((p) => p.review)]
    return { total: all.length, reviewed: all.filter((r) => r.status !== 'pending').length }
  }

  /** Deletes the screenshots of the document kept with a use: what was found and decided stays. */
  const deleteScreenshot = (analysisId: string, runId: string) =>
    attempt(async () => keepRun(analysisId, await api.putFileDecision(analysisId, runId, 'deleted')))

  /** Says the screenshots are to be kept, which stops asking. */
  const keepScreenshot = (analysisId: string, runId: string) =>
    attempt(async () => keepRun(analysisId, await api.putFileDecision(analysisId, runId, 'kept')))

  return {
    analyses,
    failed,
    actionError,
    total,
    find,
    findRun,
    canAccess,
    accessible,
    registerView,
    modelNames,
    createAnalysis,
    remove,
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
