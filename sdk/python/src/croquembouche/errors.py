"""What goes wrong, as exceptions that say what: the API answers with a status and a `detail`, which is kept."""

import httpx2


class CroquembouchError(Exception):
    """Anything the SDK raises on purpose."""


class APIError(CroquembouchError):
    """The API refused, or failed. `status_code` is its answer and `detail` the reason it gave, for a person to read."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class AuthenticationError(APIError):
    """401: no token, a token that is not valid (or is no longer), or a token Keycloak would not give."""


class ForbiddenError(APIError):
    """403: the token is good but may not do this (a service account that reads the catalogue changes nothing)."""


class NotFoundError(APIError):
    """404: there is no such thing, or it is not for this token to know of (a model it cannot use does not exist)."""


class InvalidRequestError(APIError):
    """400 or 422: what was sent cannot be kept; `detail` says why."""


class ConflictError(APIError):
    """409: what is asked cannot be done in the state things are in (a model an analysis uses is not deleted)."""


class ServerError(APIError):
    """5xx: the API failed."""


class WaitTimeoutError(CroquembouchError, TimeoutError):
    """What was waited for (a use of an analysis, a search) did not end in time. It goes on, on the server: it can be
    waited for again, or cancelled."""


class RunFailedError(CroquembouchError):
    """The use of the analysis ended as failed (the worker could not match the document)."""


def detail_of(response: httpx2.Response) -> str:
    """The reason in an answer of the API: its `detail`, which is a text, or a list of what is not valid."""
    try:
        detail = response.json()["detail"]
    except Exception:
        return response.text or response.reason_phrase
    if isinstance(detail, list):
        return "; ".join(
            f"{'.'.join(str(p) for p in d.get('loc', []))}: {d.get('msg', '')}".strip(": ") for d in detail
        )
    return str(detail)


def error_for(response: httpx2.Response) -> APIError:
    """The exception for an answer that is an error."""
    status, detail = response.status_code, detail_of(response)
    kind = {401: AuthenticationError, 403: ForbiddenError, 404: NotFoundError, 409: ConflictError}.get(status)
    if kind is None:
        kind = InvalidRequestError if status in (400, 422) else ServerError if status >= 500 else APIError
    return kind(status, detail)
