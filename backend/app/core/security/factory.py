import os
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import KeycloakSettings
from app.core.security.claims import extract_identity
from app.core.security.keycloak_client import keycloak_openid, session_store

# The role (of the client of the backend) of the service accounts that read every model, whoever it is for.
CATALOGUE_READER = "catalogue-reader"

# What a token says on its own, that the user info does not always repeat.
_TOKEN_CLAIMS = ("resource_access", "groups", "clientId")


@dataclass
class RequestContext:
    user_id: str
    email: str
    roles: list[str]
    is_admin: bool
    first_name: str = ""
    last_name: str = ""
    groups: list[str] = field(default_factory=list)
    # The client of a service account, which is no person: empty for anyone else.
    service_client_id: str = ""
    # The user's own access token, for what is called on their behalf: kept out of every repr and log, never stored.
    access_token: str | None = field(default=None, repr=False)

    @property
    def is_catalogue_reader(self) -> bool:
        """A service account that was given the role to read the whole catalogue, and nothing else: recognised by its
        client and its role, not by being an administrator. A person with the role is no more than a person."""
        return bool(self.service_client_id) and CATALOGUE_READER in self.roles


class KeycloakToken:
    """Real verifier: a bearer access token (non-browser clients) or the BFF
    session cookie set by /api/auth/callback (browser clients)."""

    def __init__(self) -> None:
        self._keycloak_settings = KeycloakSettings()

    def __call__(self, request: Request) -> RequestContext:
        identity = self._from_bearer_token(request) or self._from_session_cookie(request)
        if identity is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return RequestContext(**identity)

    def _from_bearer_token(self, request: Request) -> dict | None:
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None
        token = authorization.removeprefix("Bearer ")
        try:
            # userinfo, not introspect: introspection requires the caller to be
            # in the token's own audience, which a resource server usually isn't.
            claims = keycloak_openid.userinfo(token)
        except Exception:
            return None
        # The token was just accepted by Keycloak, so what it says can be read as it is. It is where the roles of a
        # client are by default, and where a service account says which client it is; the user info wins if it has them.
        payload = self._payload(token)
        if not self._is_for_us(payload):
            return None
        claims = {**{k: payload[k] for k in _TOKEN_CLAIMS if k in payload}, **claims}
        identity = extract_identity(claims, self._keycloak_settings.KEYCLOAK_CLIENT_ID)
        return {**identity, "access_token": token} if identity else None

    @staticmethod
    def _payload(token: str) -> dict:
        try:
            payload = keycloak_openid.decode_token(token, validate=False)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _is_for_us(self, payload: dict) -> bool:
        """Whether the token is meant for Croquembouche, when the audience is asked for: it was issued to the client, or
        names it in its audience (a token exchanged for it, or a service account that has a role of its client)."""
        audience = self._keycloak_settings.KEYCLOAK_AUDIENCE
        if not audience:
            return True
        named = payload.get("aud") or []
        return audience in ([named] if isinstance(named, str) else named) or payload.get("azp") == audience

    def _from_session_cookie(self, request: Request) -> dict | None:
        session_id = request.cookies.get(self._keycloak_settings.SESSION_COOKIE_NAME)
        if not session_id:
            return None
        session = session_store.get_session(session_id)
        if session is None:
            return None
        return {**session.identity, "access_token": session.access_token}


class AllowAllAccess:
    """Dev/test verifier: no Keycloak, no Redis - a fixed identity for every
    request. Selected via VERIFY_TOKEN_MODEL=full-access (unit tests)."""

    def __call__(self, request: Request) -> RequestContext:
        return RequestContext(user_id="dev-user", email="dev@example.com", roles=["admin"], is_admin=True)


SECURITY_FACTORY = {"full-access": AllowAllAccess, "keycloak": KeycloakToken}


def get_token_verifier():
    strategy = SECURITY_FACTORY[os.environ.get("VERIFY_TOKEN_MODEL", "keycloak")]
    return strategy()


TokenVerifier = get_token_verifier()

# Declared purely so Swagger UI shows an "Authorize" button for a bearer token; the extraction itself happens in
# KeycloakToken. auto_error=False: a request without the header must still fall through to the session cookie.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Keycloak access token. Browser clients authenticate via the BFF session cookie instead.",
)
_bearer_security = Security(bearer_scheme)


def get_current_user(
    request: Request, _credentials: Annotated[HTTPAuthorizationCredentials | None, _bearer_security] = None
) -> RequestContext:
    """Who is asking according to their token or their session."""
    return TokenVerifier(request)
