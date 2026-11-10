import { ok } from './http.js';
/** The tasks the workers declare: each instance of a worker registers what it can be given when it starts, and says it
 *  is alive every few seconds. A task is listed for each name and version, with the instances that have it. */
export class Tasks {
    http;
    constructor(http) {
        this.http = http;
    }
    /** The tasks, by name then version (the newest last). `online`: only those an instance that is alive has. */
    list({ online = false } = {}) {
        return ok(this.http.GET('/api/tasks', { params: { query: { online } } }));
    }
    /** The versions of a task, with the instances that have each; a `NotFoundError` when no worker declares it. A task
     *  says what it takes (`inputSchema`), what can be set (`parameters`) and what it gives (`outputSchema`), as JSON
     *  Schemas. */
    get(name, { online = false } = {}) {
        return ok(this.http.GET('/api/tasks/{name}', { params: { path: { name }, query: { online } } }));
    }
}
