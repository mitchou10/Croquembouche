import { type Document, asForm, formWith } from './files.js'
import { type Http, ok } from './http.js'
import { CroquembouchError, RunFailedError, WaitTimeoutError } from './errors.js'
import type { AnalysisCreate, AnalysisOut, DetectionOut, EntityOut, PageOut, RunOut, Share, TemplateOut } from './types.js'
import type { Templates } from './templates.js'

/** What `wait()` takes. */
export interface WaitOptions {
  /** How long to wait, in milliseconds; `null` waits for ever. 5 minutes by default. */
  timeoutMs?: number | null
  /** How often to ask, in milliseconds. 1 second by default. */
  intervalMs?: number
  /** Also wait for the text of the document to be read (and the entities found in it). On by default. */
  text?: boolean
  /** Gives up waiting (the use goes on, on the server). */
  signal?: AbortSignal
}

/** Something the analysis found in the document: the entity of a model it carried a zone over to (or found in the text),
 *  where, what is written there and how sure the analysis is. */
export interface Element {
  id: string
  detection: DetectionOut
  /** The entity it is, when it is known (the model may have been deleted since, or not be readable by the token). */
  entity?: EntityOut
  /** The model it is most likely taken for; absent when « other » is likelier. */
  template?: TemplateOut
  /** What the OCR read in the zone: absent for an image or a table, and until the text is read. */
  text?: string
  /** How sure the analysis is of the likeliest class (0 to 1). */
  confidence: number
  zone: DetectionOut['zone']
  /** Which of the zones of its entity it was found from, for an entity that has several (from 0). */
  zoneIndex?: number
}

/** What a use of an analysis found, once it has ended: the class of each page and the elements found. */
export interface RunResult {
  run: RunOut
  status: RunOut['status']
  pages: PageOut[]
  elements: Element[]
}

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason)
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        reject(signal.reason)
      },
      { once: true },
    )
  })
}

/** One use of an analysis on a document: it runs on the server, and `wait()` brings the result. */
export class Run {
  constructor(
    private readonly analyses: Analyses,
    readonly analysisId: string,
    public data: RunOut,
  ) {}

  get id(): string {
    return this.data.id
  }

  get status(): RunOut['status'] {
    return this.data.status
  }

  get ended(): boolean {
    return this.data.status !== 'running'
  }

  /** Reads the use again. */
  async refresh(): Promise<RunOut> {
    this.data = await this.analyses.runData(this.analysisId, this.id)
    return this.data
  }

  /** Stops it, if it is still running. */
  async cancel(): Promise<RunOut> {
    this.data = await this.analyses.cancelRun(this.analysisId, this.id)
    return this.data
  }

  /** Ended, and (when the text is wanted) the text is read and the entities with no zone are found in it. */
  private settled(text: boolean): boolean {
    if (!this.ended) return false
    return !text || (this.data.ocrStatus !== 'running' && !['waiting', 'running'].includes(this.data.findStatus ?? 'none'))
  }

  /** Waits for the use to end, asking every `intervalMs`, and gives its result.
   *
   *  Throws a `WaitTimeoutError` after `timeoutMs`: the use goes on, and can be waited for again or cancelled. Throws a
   *  `RunFailedError` if it failed. */
  async wait({ timeoutMs = 300_000, intervalMs = 1000, text = true, signal }: WaitOptions = {}): Promise<RunResult> {
    const started = Date.now()
    for (;;) {
      await this.refresh()
      if (this.settled(text)) break
      if (timeoutMs !== null && Date.now() - started >= timeoutMs) {
        throw new WaitTimeoutError(`The use ${this.id} was still ${this.status} after ${timeoutMs} ms.`)
      }
      await sleep(intervalMs, signal)
    }
    if (this.status === 'failed') {
      throw new RunFailedError(`The use ${this.id} of the analysis ${this.analysisId} failed.`)
    }
    return this.analyses.resultOf(this.analysisId, this.data)
  }
}

/** The analyses: what to look for (models of the catalogue, a version of them), and the documents tried on it. */
export class Analyses {
  constructor(
    private readonly http: Http,
    private readonly templates: Templates,
  ) {}

  /** The analyses the token can see (the ones it cannot open are only named). */
  list(): Promise<AnalysisOut[]> {
    return ok(this.http.GET('/api/analyses'))
  }

  get(analysisId: string): Promise<AnalysisOut> {
    return ok(this.http.GET('/api/analyses/{analysis_id}', { params: { path: { analysis_id: analysisId } } }))
  }

  /** Makes an analysis of models of the catalogue. `templateVersions` pins some of them to a version (X.Y.Z), by id: they
   *  are looked for as they were then, so that what is found can be played again. The results are the token's own. */
  create(
    name: string,
    templateIds: string[],
    options: {
      description?: string
      templateVersions?: Record<string, string>
      isPublic?: boolean
      shares?: Share[]
    } = {},
  ): Promise<AnalysisOut> {
    const body: AnalysisCreate = {
      name,
      templateIds,
      description: options.description ?? '',
      isPublic: options.isPublic ?? false,
      shares: options.shares ?? [],
      templateVersions: options.templateVersions ?? {},
    }
    return ok(this.http.POST('/api/analyses', { body }))
  }

  async delete(analysisId: string): Promise<void> {
    await ok(this.http.DELETE('/api/analyses/{analysis_id}', { params: { path: { analysis_id: analysisId } } }))
  }

  /** Tries the analysis on a document (its bytes, a `File`, or in Node the path of a file): the use starts at once, and
   *  `await run.wait()` gives its result. The screenshot of the document is let go of when the result is read, unless
   *  `keepScreenshot`. */
  async run(
    analysisId: string,
    document: Document,
    { filename, keepScreenshot = false }: { filename?: string; keepScreenshot?: boolean } = {},
  ): Promise<Run> {
    const form = await formWith(document, filename, { keepScreenshot })
    const data = await ok(
      this.http.POST('/api/analyses/{analysis_id}/runs', {
        params: { path: { analysis_id: analysisId } },
        ...asForm(form),
      }),
    )
    return new Run(this, analysisId, data)
  }

  /** A use that was started (by this token: what a use found is its person's alone). */
  async getRun(analysisId: string, runId: string): Promise<Run> {
    return new Run(this, analysisId, await this.runData(analysisId, runId))
  }

  /** @internal */
  runData(analysisId: string, runId: string): Promise<RunOut> {
    return ok(
      this.http.GET('/api/analyses/{analysis_id}/runs/{run_id}', {
        params: { path: { analysis_id: analysisId, run_id: runId } },
      }),
    )
  }

  /** @internal */
  cancelRun(analysisId: string, runId: string): Promise<RunOut> {
    return ok(
      this.http.POST('/api/analyses/{analysis_id}/runs/{run_id}/cancel', {
        params: { path: { analysis_id: analysisId, run_id: runId } },
      }),
    )
  }

  /** The models an analysis looks for and their sub-models, by id: what names the entities of its results. One the token
   *  cannot read is left out. */
  private async models(analysisId: string): Promise<Map<string, TemplateOut>> {
    const analysis = await this.get(analysisId)
    const found = new Map<string, TemplateOut>()
    const wanted = [...analysis.templateIds]
    for (let id = wanted.pop(); id !== undefined; id = wanted.pop()) {
      if (found.has(id)) continue
      try {
        const template = await this.templates.get(id)
        found.set(id, template)
        wanted.push(...(template.children ?? []).map((c) => c.id))
      } catch (error) {
        if (!(error instanceof CroquembouchError)) throw error
      }
    }
    return found
  }

  /** @internal */
  async resultOf(analysisId: string, run: RunOut): Promise<RunResult> {
    const models = await this.models(analysisId)
    const entities = new Map([...models.values()].flatMap((t) => t.entities.map((e) => [e.id, e] as const)))
    const elements = (run.detections ?? []).map((detection): Element => {
      const best = detection.classifications[0]?.templateId ?? undefined
      return {
        id: detection.id,
        detection,
        entity: detection.entityId ? entities.get(detection.entityId) : undefined,
        template: best ? models.get(best) : undefined,
        text: detection.text ?? undefined,
        confidence: detection.classifications[0]?.confidence ?? 0,
        zone: detection.zone,
        zoneIndex: detection.zoneIndex ?? undefined,
      }
    })
    return { run, status: run.status, pages: run.pages ?? [], elements }
  }
}
