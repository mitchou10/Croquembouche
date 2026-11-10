import { type Http } from './http.js';
import type { TaskOut } from './types.js';
/** The tasks the workers declare: each instance of a worker registers what it can be given when it starts, and says it
 *  is alive every few seconds. A task is listed for each name and version, with the instances that have it. */
export declare class Tasks {
    private readonly http;
    constructor(http: Http);
    /** The tasks, by name then version (the newest last). `online`: only those an instance that is alive has. */
    list({ online }?: {
        online?: boolean;
    }): Promise<TaskOut[]>;
    /** The versions of a task, with the instances that have each; a `NotFoundError` when no worker declares it. A task
     *  says what it takes (`inputSchema`), what can be set (`parameters`) and what it gives (`outputSchema`), as JSON
     *  Schemas. */
    get(name: string, { online }?: {
        online?: boolean;
    }): Promise<TaskOut[]>;
}
