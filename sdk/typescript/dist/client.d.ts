import { type TokenSource } from './auth.js';
import { Analyses } from './analyses.js';
import { Searches } from './searches.js';
import { Tasks } from './tasks.js';
import { Templates } from './templates.js';
import { Users } from './users.js';
export interface CroquembouchOptions {
    /** How to sign in: any of `bearerToken`, `clientCredentials` or `tokenExchange` (they renew themselves). */
    auth?: TokenSource;
    /** A token the program has (it is not renewed). */
    token?: string;
    /** A service account: the token endpoint of Keycloak (see `keycloakTokenUrl`), with `clientId` and `clientSecret`. */
    tokenUrl?: string;
    clientId?: string;
    clientSecret?: string;
    /** How long a request may take, in milliseconds. 30 seconds by default. */
    timeoutMs?: number;
    /** The `fetch` to use: the global one by default. */
    fetch?: typeof fetch;
}
/** A client of the API::
 *
 *      const client = new Croquembouche(url, { tokenUrl, clientId, clientSecret })
 *      const form = await client.templates.get(templateId)
 *      const run = await client.analyses.run(analysisId, 'scan.pdf')
 *      const result = await run.wait()
 *
 *  How it signs in, from the least to the most to say: nothing (a backend that asks for nothing), `token` (one the program
 *  has), `tokenUrl` with `clientId` and `clientSecret` (a service account, which gets its own token and renews it), or
 *  `auth` with any of `bearerToken`, `clientCredentials` or `tokenExchange`. */
export declare class Croquembouche {
    readonly templates: Templates;
    readonly analyses: Analyses;
    readonly searches: Searches;
    readonly tasks: Tasks;
    readonly users: Users;
    constructor(url: string, options?: CroquembouchOptions);
}
