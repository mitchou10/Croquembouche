"""Tokens: the SDK asks Keycloak for them when it has none, and again before the one it has runs out.

Three ways to have one, all of them renewing themselves: a service account (`ClientCredentials`), the token of a person
exchanged for one meant for Croquembouche (`TokenExchange`), or a token the program already has (`BearerToken`).
"""

import asyncio
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from inspect import isawaitable

import httpx2

from .errors import AuthenticationError

# How long before it runs out a token is replaced: a request made with it must not arrive too late.
LEEWAY = 30.0
TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"

TokenProvider = Callable[[], str | Awaitable[str]]


def token_url(keycloak_url: str, realm: str) -> str:
    """The token endpoint of a realm of Keycloak."""
    return f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"


class BearerToken(httpx2.Auth):
    """A token the program has: the text of it, or a function that gives the current one (called for each request, so
    it can renew it). It is not renewed here."""

    def __init__(self, token: str | TokenProvider) -> None:
        self._token = token

    async def _current(self) -> str:
        token = self._token() if callable(self._token) else self._token
        return await token if isawaitable(token) else token

    async def async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        request.headers["Authorization"] = f"Bearer {await self._current()}"
        yield request


class _Renewing(httpx2.Auth):
    """A token got from Keycloak, kept until it is about to run out. One request at a time asks for the next one, and a
    401 (a token that was revoked) is answered by asking again, once."""

    def __init__(
        self,
        url: str,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url
        self._transport = transport
        self._clock = clock
        self._token: str | None = None
        self._expires = 0.0
        self._lock = asyncio.Lock()

    async def _form(self) -> dict[str, str]:
        raise NotImplementedError

    async def _fresh(self) -> str:
        async with self._lock:
            if self._token is None or self._clock() >= self._expires:
                await self._renew()
            assert self._token is not None
            return self._token

    async def _renew(self) -> None:
        async with httpx2.AsyncClient(transport=self._transport) as http:
            response = await http.post(self._url, data=await self._form())
        if response.status_code >= 400:
            try:
                reason = response.json().get("error_description") or response.json().get("error")
            except Exception:
                reason = None
            raise AuthenticationError(response.status_code, reason or f"Keycloak refused the token ({self._url}).")
        body = response.json()
        self._token = body["access_token"]
        self._expires = self._clock() + max(float(body.get("expires_in", 60)) - LEEWAY, 0.0)

    async def async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        request.headers["Authorization"] = f"Bearer {await self._fresh()}"
        response = yield request
        if response.status_code == 401:
            self._token = None
            request.headers["Authorization"] = f"Bearer {await self._fresh()}"
            yield request


class ClientCredentials(_Renewing):
    """A service account: the application is its own caller (`client_credentials`), with no person behind it."""

    def __init__(
        self, token_url: str, client_id: str, client_secret: str, *, scope: str | None = None, **kwargs
    ) -> None:
        super().__init__(token_url, **kwargs)
        self._form_data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        if scope:
            self._form_data["scope"] = scope

    async def _form(self) -> dict[str, str]:
        return self._form_data


class TokenExchange(_Renewing):
    """The token of a person exchanged (RFC 8693) for one meant for Croquembouche: what is done with it is done as that
    person. `subject_token` is their token, or a function that gives the current one (it is asked for again each time
    the exchanged token is renewed)."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        subject_token: str | TokenProvider,
        *,
        audience: str = "croquembouche-backend",
        **kwargs,
    ) -> None:
        super().__init__(token_url, **kwargs)
        self._client = (client_id, client_secret)
        self._subject = subject_token
        self._audience = audience

    async def _form(self) -> dict[str, str]:
        subject = self._subject() if callable(self._subject) else self._subject
        return {
            "grant_type": TOKEN_EXCHANGE,
            "client_id": self._client[0],
            "client_secret": self._client[1],
            "subject_token": await subject if isawaitable(subject) else subject,
            "subject_token_type": ACCESS_TOKEN,
            "requested_token_type": ACCESS_TOKEN,
            "audience": self._audience,
        }
