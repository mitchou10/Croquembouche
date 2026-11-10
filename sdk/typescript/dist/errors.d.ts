/** Anything the SDK throws on purpose. */
export declare class CroquembouchError extends Error {
    name: string;
}
/** The API refused, or failed. `status` is its answer and `detail` the reason it gave, for a person to read. */
export declare class APIError extends CroquembouchError {
    readonly status: number;
    readonly detail: string;
    name: string;
    constructor(status: number, detail: string);
}
/** 401: no token, a token that is not valid (or is no longer), or a token Keycloak would not give. */
export declare class AuthenticationError extends APIError {
    name: string;
}
/** 403: the token is good but may not do this (a service account that reads the catalogue changes nothing). */
export declare class ForbiddenError extends APIError {
    name: string;
}
/** 404: there is no such thing, or it is not for this token to know of (a model it cannot use does not exist). */
export declare class NotFoundError extends APIError {
    name: string;
}
/** 400 or 422: what was sent cannot be kept; `detail` says why. */
export declare class InvalidRequestError extends APIError {
    name: string;
}
/** 409: what is asked cannot be done in the state things are in (a model an analysis uses is not deleted). */
export declare class ConflictError extends APIError {
    name: string;
}
/** 5xx: the API failed. */
export declare class ServerError extends APIError {
    name: string;
}
/** What was waited for (a use of an analysis, a search) did not end in time. It goes on, on the server: it can be
 *  waited for again, or cancelled. */
export declare class WaitTimeoutError extends CroquembouchError {
    name: string;
}
/** The use of the analysis ended as failed (the worker could not match the document). */
export declare class RunFailedError extends CroquembouchError {
    name: string;
}
/** The reason in an answer of the API: its `detail`, which is a text, or a list of what is not valid. */
export declare function detailOf(body: unknown, fallback: string): string;
/** The error for an answer that is an error. */
export declare function errorFor(status: number, body: unknown, fallback?: string): APIError;
