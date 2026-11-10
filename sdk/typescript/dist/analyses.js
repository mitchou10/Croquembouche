import { asForm, formWith } from './files.js';
import { ok } from './http.js';
import { CroquembouchError, RunFailedError, WaitTimeoutError } from './errors.js';
export function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
        if (signal?.aborted)
            return reject(signal.reason);
        const timer = setTimeout(resolve, ms);
        signal?.addEventListener('abort', () => {
            clearTimeout(timer);
            reject(signal.reason);
        }, { once: true });
    });
}
/** One use of an analysis on a document: it runs on the server, and `wait()` brings the result. */
export class Run {
    analyses;
    analysisId;
    data;
    constructor(analyses, analysisId, data) {
        this.analyses = analyses;
        this.analysisId = analysisId;
        this.data = data;
    }
    get id() {
        return this.data.id;
    }
    get status() {
        return this.data.status;
    }
    get ended() {
        return this.data.status !== 'running';
    }
    /** Reads the use again. */
    async refresh() {
        this.data = await this.analyses.runData(this.analysisId, this.id);
        return this.data;
    }
    /** Stops it, if it is still running. */
    async cancel() {
        this.data = await this.analyses.cancelRun(this.analysisId, this.id);
        return this.data;
    }
    /** Ended, and (when the text is wanted) the text is read and the entities with no zone are found in it. */
    settled(text) {
        if (!this.ended)
            return false;
        return !text || (this.data.ocrStatus !== 'running' && !['waiting', 'running'].includes(this.data.findStatus ?? 'none'));
    }
    /** Waits for the use to end, asking every `intervalMs`, and gives its result.
     *
     *  Throws a `WaitTimeoutError` after `timeoutMs`: the use goes on, and can be waited for again or cancelled. Throws a
     *  `RunFailedError` if it failed. */
    async wait({ timeoutMs = 300_000, intervalMs = 1000, text = true, signal } = {}) {
        const started = Date.now();
        for (;;) {
            await this.refresh();
            if (this.settled(text))
                break;
            if (timeoutMs !== null && Date.now() - started >= timeoutMs) {
                throw new WaitTimeoutError(`The use ${this.id} was still ${this.status} after ${timeoutMs} ms.`);
            }
            await sleep(intervalMs, signal);
        }
        if (this.status === 'failed') {
            throw new RunFailedError(`The use ${this.id} of the analysis ${this.analysisId} failed.`);
        }
        return this.analyses.resultOf(this.analysisId, this.data);
    }
}
/** The analyses: what to look for (models of the catalogue, a version of them), and the documents tried on it. */
export class Analyses {
    http;
    templates;
    constructor(http, templates) {
        this.http = http;
        this.templates = templates;
    }
    /** The analyses the token can see (the ones it cannot open are only named). */
    list() {
        return ok(this.http.GET('/api/analyses'));
    }
    get(analysisId) {
        return ok(this.http.GET('/api/analyses/{analysis_id}', { params: { path: { analysis_id: analysisId } } }));
    }
    /** Makes an analysis of models of the catalogue. `templateVersions` pins some of them to a version (X.Y.Z), by id: they
     *  are looked for as they were then, so that what is found can be played again. The results are the token's own. */
    create(name, templateIds, options = {}) {
        const body = {
            name,
            templateIds,
            description: options.description ?? '',
            isPublic: options.isPublic ?? false,
            shares: options.shares ?? [],
            templateVersions: options.templateVersions ?? {},
        };
        return ok(this.http.POST('/api/analyses', { body }));
    }
    async delete(analysisId) {
        await ok(this.http.DELETE('/api/analyses/{analysis_id}', { params: { path: { analysis_id: analysisId } } }));
    }
    /** Tries the analysis on a document (its bytes, a `File`, or in Node the path of a file): the use starts at once, and
     *  `await run.wait()` gives its result. The screenshot of the document is let go of when the result is read, unless
     *  `keepScreenshot`. */
    async run(analysisId, document, { filename, keepScreenshot = false } = {}) {
        const form = await formWith(document, filename, { keepScreenshot });
        const data = await ok(this.http.POST('/api/analyses/{analysis_id}/runs', {
            params: { path: { analysis_id: analysisId } },
            ...asForm(form),
        }));
        return new Run(this, analysisId, data);
    }
    /** A use that was started (by this token: what a use found is its person's alone). */
    async getRun(analysisId, runId) {
        return new Run(this, analysisId, await this.runData(analysisId, runId));
    }
    /** @internal */
    runData(analysisId, runId) {
        return ok(this.http.GET('/api/analyses/{analysis_id}/runs/{run_id}', {
            params: { path: { analysis_id: analysisId, run_id: runId } },
        }));
    }
    /** @internal */
    cancelRun(analysisId, runId) {
        return ok(this.http.POST('/api/analyses/{analysis_id}/runs/{run_id}/cancel', {
            params: { path: { analysis_id: analysisId, run_id: runId } },
        }));
    }
    /** The models an analysis looks for and their sub-models, by id: what names the entities of its results. One the token
     *  cannot read is left out. */
    async models(analysisId) {
        const analysis = await this.get(analysisId);
        const found = new Map();
        const wanted = [...analysis.templateIds];
        for (let id = wanted.pop(); id !== undefined; id = wanted.pop()) {
            if (found.has(id))
                continue;
            try {
                const template = await this.templates.get(id);
                found.set(id, template);
                wanted.push(...(template.children ?? []).map((c) => c.id));
            }
            catch (error) {
                if (!(error instanceof CroquembouchError))
                    throw error;
            }
        }
        return found;
    }
    /** @internal */
    async resultOf(analysisId, run) {
        const models = await this.models(analysisId);
        const entities = new Map([...models.values()].flatMap((t) => t.entities.map((e) => [e.id, e])));
        const elements = (run.detections ?? []).map((detection) => {
            const best = detection.classifications[0]?.templateId ?? undefined;
            return {
                id: detection.id,
                detection,
                entity: detection.entityId ? entities.get(detection.entityId) : undefined,
                template: best ? models.get(best) : undefined,
                text: detection.text ?? undefined,
                confidence: detection.classifications[0]?.confidence ?? 0,
                zone: detection.zone,
                zoneIndex: detection.zoneIndex ?? undefined,
            };
        });
        return { run, status: run.status, pages: run.pages ?? [], elements };
    }
}
