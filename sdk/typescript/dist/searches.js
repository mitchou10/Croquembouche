import { asForm, formWith } from './files.js';
import { ok } from './http.js';
import { WaitTimeoutError } from './errors.js';
import { sleep } from './analyses.js';
/** A search for the pages of the catalogue that look like the pages of a document: it runs on the server. */
export class Search {
    searches;
    data;
    constructor(searches, data) {
        this.searches = searches;
        this.data = data;
    }
    get id() {
        return this.data.id;
    }
    get status() {
        return this.data.status;
    }
    async refresh() {
        this.data = await this.searches.get(this.id);
        return this.data;
    }
    /** Waits for the search to end, and gives it: its `neighbours` (the pages that look like those of the document, the
     *  likeliest first) and the `links` between them. Throws a `WaitTimeoutError` after `timeoutMs` (5 minutes by default,
     *  `null` waits for ever). */
    async wait({ timeoutMs = 300_000, intervalMs = 1000, signal, } = {}) {
        const started = Date.now();
        for (;;) {
            await this.refresh();
            if (this.status !== 'running')
                return this.data;
            if (timeoutMs !== null && Date.now() - started >= timeoutMs) {
                throw new WaitTimeoutError(`The search ${this.id} was still running after ${timeoutMs} ms.`);
            }
            await sleep(intervalMs, signal);
        }
    }
}
export class Searches {
    http;
    constructor(http) {
        this.http = http;
    }
    /** Looks for the pages of the catalogue like those of a document: `k` neighbours for each page, among the models asked
     *  for or among every one the token can use. */
    async start(document, { k = 5, templateIds, filename } = {}) {
        const form = await formWith(document, filename, { k });
        for (const id of templateIds ?? [])
            form.append('templateIds', id);
        return new Search(this, await ok(this.http.POST('/api/searches', asForm(form))));
    }
    get(searchId) {
        return ok(this.http.GET('/api/searches/{search_id}', { params: { path: { search_id: searchId } } }));
    }
    /** The searches of the token. */
    list() {
        return ok(this.http.GET('/api/searches'));
    }
    async delete(searchId) {
        await ok(this.http.DELETE('/api/searches/{search_id}', { params: { path: { search_id: searchId } } }));
    }
}
