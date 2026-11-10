/** How long before it runs out a token is replaced (seconds): a request made with it must not arrive too late. */
export declare const LEEWAY = 30;
type Maybe<T> = T | Promise<T>;
export type TokenProvider = () => Maybe<string>;
/** Where the SDK gets the token of a request. `invalidate` is called when the API answered 401 to the one it gave: the
 *  next `token()` is a new one. */
export interface TokenSource {
    token(): Promise<string>;
    invalidate?(): void;
}
interface Renewal {
    /** The token endpoint of Keycloak (see `keycloakTokenUrl`). */
    tokenUrl: string;
    /** For tests: the `fetch` to use, and the clock (milliseconds). */
    fetch?: typeof fetch;
    now?: () => number;
}
/** The token endpoint of a realm of Keycloak. */
export declare function keycloakTokenUrl(keycloakUrl: string, realm: string): string;
/** A token the program has: the text of it, or a function that gives the current one (called for each request, so it can
 *  renew it). It is not renewed here. */
export declare function bearerToken(token: string | TokenProvider): TokenSource;
/** A service account: the application is its own caller (`client_credentials`), with no person behind it. */
export declare function clientCredentials(options: Renewal & {
    clientId: string;
    clientSecret: string;
    scope?: string;
}): TokenSource;
/** The token of a person exchanged (RFC 8693) for one meant for Croquembouche: what is done with it is done as that
 *  person. `subjectToken` is their token, or a function that gives the current one (it is asked for again each time the
 *  exchanged token is renewed). */
export declare function tokenExchange(options: Renewal & {
    clientId: string;
    clientSecret: string;
    subjectToken: string | TokenProvider;
    audience?: string;
}): TokenSource;
export {};
