import { type Http } from './http.js';
import type { PurgeOut } from './types.js';
/** What a person sent to be analysed, and forgetting it. */
export declare class Users {
    private readonly http;
    constructor(http: Http);
    /** Deletes what the token sent to be analysed: its uses of analyses, its searches and the documents it sent. Not the
     *  models, nor their example documents, nor the analyses. For a service account, that is all that it sent. */
    purgeMyData(): Promise<PurgeOut>;
    /** The same for another person (the identifier of their account): administrators only (`ForbiddenError`). */
    purge(userId: string): Promise<PurgeOut>;
}
