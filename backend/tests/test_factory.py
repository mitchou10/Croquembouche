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


# --- service accounts and exchanged tokens


def _token_says(payload: dict) -> None:
    factory.keycloak_openid.decode_token.return_value = payload


def test_a_service_account_is_known_by_its_client_and_its_role(verifier):
    # The user info says who; the token says which client it is and the roles that the user info leaves out.
    factory.keycloak_openid.userinfo.return_value = {"sub": "sa1", "preferred_username": "service-account-mf"}
    _token_says(
        {"clientId": "mille-feuille", "resource_access": {"croquembouche-backend": {"roles": ["catalogue-reader"]}}}
    )

    context = verifier(_request({"Authorization": "Bearer tok"}))

    assert context.service_client_id == "mille-feuille" and context.is_catalogue_reader
    assert not context.is_admin


def test_a_person_with_the_role_is_not_a_reader(verifier):
    factory.keycloak_openid.userinfo.return_value = {
        "sub": "u1",
        "resource_access": {"croquembouche-backend": {"roles": ["catalogue-reader"]}},
    }
    _token_says({})

    context = verifier(_request({"Authorization": "Bearer tok"}))

    assert context.service_client_id == "" and not context.is_catalogue_reader


def test_the_user_info_wins_over_the_token(verifier):
    factory.keycloak_openid.userinfo.return_value = {
        "sub": "u1",
        "groups": ["/team"],
        "resource_access": {"croquembouche-backend": {"roles": ["user"]}},
    }
    _token_says({"groups": ["/other"], "resource_access": {"croquembouche-backend": {"roles": ["admin"]}}})

    context = verifier(_request({"Authorization": "Bearer tok"}))

    assert context.groups == ["/team"] and context.roles == ["user"] and not context.is_admin


@pytest.mark.parametrize(
    ("payload", "accepted"),
    [
        ({"aud": ["croquembouche-backend", "account"]}, True),  # exchanged for Croquembouche
        ({"aud": "croquembouche-backend"}, True),
        ({"aud": "account", "azp": "croquembouche-backend"}, True),  # issued to Croquembouche itself
        ({"aud": ["account"], "azp": "other"}, False),
        ({}, False),
    ],
)
def test_the_audience_is_asked_for_when_it_is_set(verifier, monkeypatch, payload, accepted):
    monkeypatch.setattr(verifier._keycloak_settings, "KEYCLOAK_AUDIENCE", "croquembouche-backend")
    factory.keycloak_openid.userinfo.return_value = CLAIMS
    factory.session_store.get_session.return_value = None
    _token_says(payload)

    if accepted:
        assert verifier(_request({"Authorization": "Bearer tok"})).user_id == "u1"
    else:
        with pytest.raises(HTTPException) as error:
            verifier(_request({"Authorization": "Bearer tok"}))
        assert error.value.status_code == 401


def test_the_identity_of_an_exchanged_token_is_the_persons(verifier, monkeypatch):
    monkeypatch.setattr(verifier._keycloak_settings, "KEYCLOAK_AUDIENCE", "croquembouche-backend")
    factory.keycloak_openid.userinfo.return_value = {"sub": "julie", "email": "julie@example.org", "groups": ["/team"]}
    _token_says({"aud": ["croquembouche-backend"], "azp": "mille-feuille"})

    context = verifier(_request({"Authorization": "Bearer exchanged"}))

    assert (context.user_id, context.email, context.groups) == ("julie", "julie@example.org", ["/team"])
    assert context.service_client_id == "" and context.access_token == "exchanged"
