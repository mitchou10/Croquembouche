import { type Document } from './files.js';
import { type Http } from './http.js';
import type { AnalysisOut, DetectionOut, EntityOut, PageOut, RunOut, Share, TemplateOut } from './types.js';
import type { Templates } from './templates.js';
/** What `wait()` takes. */
export interface WaitOptions {
    /** How long to wait, in milliseconds; `null` waits for ever. 5 minutes by default. */
    timeoutMs?: number | null;
    /** How often to ask, in milliseconds. 1 second by default. */
    intervalMs?: number;
    /** Also wait for the text of the document to be read (and the entities found in it). On by default. */
    text?: boolean;
    /** Gives up waiting (the use goes on, on the server). */
    signal?: AbortSignal;
}
/** Something the analysis found in the document: the entity of a model it carried a zone over to (or found in the text),
 *  where, what is written there and how sure the analysis is. */
export interface Element {
    id: string;
    detection: DetectionOut;
    /** The entity it is, when it is known (the model may have been deleted since, or not be readable by the token). */
    entity?: EntityOut;
    /** The model it is most likely taken for; absent when « other » is likelier. */
    template?: TemplateOut;
    /** What the OCR read in the zone: absent for an image or a table, and until the text is read. */
    text?: string;
    /** How sure the analysis is of the likeliest class (0 to 1). */
    confidence: number;
    zone: DetectionOut['zone'];
    /** Which of the zones of its entity it was found from, for an entity that has several (from 0). */
    zoneIndex?: number;
}
/** What a use of an analysis found, once it has ended: the class of each page and the elements found. */
export interface RunResult {
    run: RunOut;
    status: RunOut['status'];
    pages: PageOut[];
    elements: Element[];
}
export declare function sleep(ms: number, signal?: AbortSignal): Promise<void>;
/** One use of an analysis on a document: it runs on the server, and `wait()` brings the result. */
export declare class Run {
    private readonly analyses;
    readonly analysisId: string;
    data: RunOut;
    constructor(analyses: Analyses, analysisId: string, data: RunOut);
    get id(): string;
    get status(): RunOut['status'];
    get ended(): boolean;
    /** Reads the use again. */
    refresh(): Promise<RunOut>;
    /** Stops it, if it is still running. */
    cancel(): Promise<RunOut>;
    /** Ended, and (when the text is wanted) the text is read and the entities with no zone are found in it. */
    private settled;
    /** Waits for the use to end, asking every `intervalMs`, and gives its result.
     *
     *  Throws a `WaitTimeoutError` after `timeoutMs`: the use goes on, and can be waited for again or cancelled. Throws a
     *  `RunFailedError` if it failed. */
    wait({ timeoutMs, intervalMs, text, signal }?: WaitOptions): Promise<RunResult>;
}
/** The analyses: what to look for (models of the catalogue, a version of them), and the documents tried on it. */
export declare class Analyses {
    private readonly http;
    private readonly templates;
    constructor(http: Http, templates: Templates);
    /** The analyses the token can see (the ones it cannot open are only named). */
    list(): Promise<AnalysisOut[]>;
    get(analysisId: string): Promise<AnalysisOut>;
    /** Makes an analysis of models of the catalogue. `templateVersions` pins some of them to a version (X.Y.Z), by id: they
     *  are looked for as they were then, so that what is found can be played again. The results are the token's own. */
    create(name: string, templateIds: string[], options?: {
        description?: string;
        templateVersions?: Record<string, string>;
        isPublic?: boolean;
        shares?: Share[];
    }): Promise<AnalysisOut>;
    delete(analysisId: string): Promise<void>;
    /** Tries the analysis on a document (its bytes, a `File`, or in Node the path of a file): the use starts at once, and
     *  `await run.wait()` gives its result. The screenshot of the document is let go of when the result is read, unless
     *  `keepScreenshot`. */
    run(analysisId: string, document: Document, { filename, keepScreenshot }?: {
        filename?: string;
        keepScreenshot?: boolean;
    }): Promise<Run>;
    /** A use that was started (by this token: what a use found is its person's alone). */
    getRun(analysisId: string, runId: string): Promise<Run>;
    /** @internal */
    runData(analysisId: string, runId: string): Promise<RunOut>;
    /** @internal */
    cancelRun(analysisId: string, runId: string): Promise<RunOut>;
    /** The models an analysis looks for and their sub-models, by id: what names the entities of its results. One the token
     *  cannot read is left out. */
    private models;
    /** @internal */
    resultOf(analysisId: string, run: RunOut): Promise<RunResult>;
}
