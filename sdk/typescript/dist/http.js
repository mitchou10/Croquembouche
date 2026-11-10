// The connection: the typed client of `openapi-fetch` (its types come from the OpenAPI of the backend), with the token put
// on every request and an error status turned into the error that says so.
import createClient from 'openapi-fetch';
import { errorFor } from './errors.js';
export function createHttp(options) {
    const { auth, timeoutMs = 30_000 } = options;
    const base = options.fetch ?? ((...args) => fetch(...args));
    async function send(request) {
        if (auth)
            request.headers.set('authorization', `Bearer ${await auth.token()}`);
        const signal = AbortSignal.any([...(request.signal ? [request.signal] : []), AbortSignal.timeout(timeoutMs)]);
        return base(new Request(request, { signal }));
    }
    // A 401 is answered by asking for a new token, once: the one that was given may have been revoked.
    async function authenticated(request) {
        const again = auth?.invalidate ? request.clone() : undefined;
        const response = await send(request);
        if (response.status === 401 && again) {
            auth.invalidate();
            return send(again);
        }
        return response;
    }
    return createClient({ baseUrl: options.baseUrl.replace(/\/+$/, ''), fetch: authenticated });
}
/** What an answer gave, or the error it is. */
export async function ok(call) {
    const { data, error, response } = await call;
    if (!response.ok)
        throw errorFor(response.status, error, response.statusText);
    return data;
}
