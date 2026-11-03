from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.security import factory
from app.core.security.session import Session


def _request(headers: dict[str, str] | None = None, cookies: str = "") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    if cookies:
        raw.append((b"cookie", cookies.encode()))
    return Request({"type": "http", "headers": raw})


CLAIMS = {"sub": "u1", "email": "a@b.c", "resource_access": {"croquembouche-backend": {"roles": ["user"]}}}


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.setattr(factory, "keycloak_openid", MagicMock())
    monkeypatch.setattr(factory, "session_store", MagicMock())
    return factory.KeycloakToken()


def test_a_bearer_token_gives_the_identity(verifier):
    factory.keycloak_openid.userinfo.return_value = CLAIMS

    context = verifier(_request({"Authorization": "Bearer tok"}))

    assert context.user_id == "u1" and context.access_token == "tok" and not context.is_admin
    assert "tok" not in repr(context)


def test_a_refused_bearer_token_falls_back_to_the_cookie(verifier):
    factory.keycloak_openid.userinfo.side_effect = RuntimeError("401")
    factory.session_store.get_session.return_value = Session(
        identity={"user_id": "u2", "email": "", "roles": [], "is_admin": False},
        access_token="at",
        refresh_token="rt",
        expires_at=0,
    )

    cookie = f"{verifier._keycloak_settings.SESSION_COOKIE_NAME}=sid"
    context = verifier(_request({"Authorization": "Bearer bad"}, cookies=cookie))

    assert context.user_id == "u2" and context.access_token == "at"


def test_a_bearer_token_without_subject_is_refused(verifier):
    factory.keycloak_openid.userinfo.return_value = {"email": "a@b.c"}

    with pytest.raises(HTTPException) as error:
        verifier(_request({"Authorization": "Bearer tok"}))

    assert error.value.status_code == 401


def test_nothing_at_all_is_refused(verifier):
    with pytest.raises(HTTPException) as error:
        verifier(_request())

    assert error.value.status_code == 401


def test_an_unknown_session_is_refused(verifier):
    factory.session_store.get_session.return_value = None

    with pytest.raises(HTTPException):
        verifier(_request(cookies=f"{verifier._keycloak_settings.SESSION_COOKIE_NAME}=gone"))
