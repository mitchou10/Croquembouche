import type { TokenSource } from './auth.js';
import type { paths } from './generated/schema.js';
export interface HttpOptions {
    baseUrl: string;
    auth?: TokenSource;
    /** The `fetch` to use: the global one by default. */
    fetch?: typeof fetch;
    /** How long a request may take before it is given up, in milliseconds. */
    timeoutMs?: number;
}
export type Http = ReturnType<typeof createHttp>;
export declare function createHttp(options: HttpOptions): import("openapi-fetch").Client<paths, `${string}/${string}`>;
/** What an answer gave, or the error it is. */
export declare function ok<T>(call: Promise<{
    data?: T;
    error?: unknown;
    response: Response;
}>): Promise<T>;
