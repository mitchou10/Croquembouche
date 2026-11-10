import { type Document } from './files.js';
import { type Http } from './http.js';
import type { SearchOut, SearchSummaryOut } from './types.js';
/** A search for the pages of the catalogue that look like the pages of a document: it runs on the server. */
export declare class Search {
    private readonly searches;
    data: SearchOut;
    constructor(searches: Searches, data: SearchOut);
    get id(): string;
    get status(): SearchOut['status'];
    refresh(): Promise<SearchOut>;
    /** Waits for the search to end, and gives it: its `neighbours` (the pages that look like those of the document, the
     *  likeliest first) and the `links` between them. Throws a `WaitTimeoutError` after `timeoutMs` (5 minutes by default,
     *  `null` waits for ever). */
    wait({ timeoutMs, intervalMs, signal, }?: {
        timeoutMs?: number | null;
        intervalMs?: number;
        signal?: AbortSignal;
    }): Promise<SearchOut>;
}
export declare class Searches {
    private readonly http;
    constructor(http: Http);
    /** Looks for the pages of the catalogue like those of a document: `k` neighbours for each page, among the models asked
     *  for or among every one the token can use. */
    start(document: Document, { k, templateIds, filename }?: {
        k?: number;
        templateIds?: string[];
        filename?: string;
    }): Promise<Search>;
    get(searchId: string): Promise<SearchOut>;
    /** The searches of the token. */
    list(): Promise<SearchSummaryOut[]>;
    delete(searchId: string): Promise<void>;
}
