from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from app.core.security.session import PendingAuth
from app.routers import auth as auth_router


def _store(**attributes) -> MagicMock:
    store = MagicMock(**attributes)
    store.check_rate_limit.return_value = True
    return store


async def test_login_redirects_to_keycloak_with_pkce_params(client, monkeypatch):
    store = _store()
    monkeypatch.setattr(auth_router, "_session_store", store)

    response = await client.get("/api/auth/login", params={"redirect": "/analyses"}, follow_redirects=False)

    assert response.status_code == 307
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert query["client_id"] == [auth_router._keycloak_settings.KEYCLOAK_CLIENT_ID]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert "/protocol/openid-connect/auth" in location.path

    saved_state, saved_pending = store.save_pending.call_args[0]
    assert saved_pending.next_path == "/analyses"
    assert saved_state == query["state"][0]


async def test_login_rejects_open_redirect_and_falls_back_to_root(client, monkeypatch):
    store = _store()
    monkeypatch.setattr(auth_router, "_session_store", store)

    for target in ("https://evil.example", "//evil.example"):
        await client.get("/api/auth/login", params={"redirect": target}, follow_redirects=False)
        assert store.save_pending.call_args[0][1].next_path == "/"


async def test_login_is_rate_limited(client, monkeypatch):
    store = _store()
    store.check_rate_limit.return_value = False
    monkeypatch.setattr(auth_router, "_session_store", store)

    response = await client.get("/api/auth/login", follow_redirects=False)

    assert response.status_code == 429
    store.save_pending.assert_not_called()


def _logged_in(monkeypatch, userinfo: dict) -> MagicMock:
    store = _store()
    store.pop_pending.return_value = PendingAuth(code_verifier="verifier", next_path="/analyses")
    store.create_session.return_value = "new-session-id"
    monkeypatch.setattr(auth_router, "_session_store", store)
    openid = MagicMock()
    openid.token.return_value = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
    openid.userinfo.return_value = userinfo
    monkeypatch.setattr(auth_router, "_keycloak_openid", openid)
    return openid


async def test_callback_creates_session_and_redirects(client, monkeypatch):
    openid = _logged_in(monkeypatch, {"sub": "u1", "email": "a@b.c"})

    response = await client.get("/api/auth/callback", params={"code": "abc", "state": "xyz"}, follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == f"{auth_router._keycloak_settings.FRONTEND_URL}/analyses"
    assert openid.token.call_args.kwargs["code_verifier"] == "verifier"
    cookie = response.headers["set-cookie"]
    assert f"{auth_router._keycloak_settings.SESSION_COOKIE_NAME}=new-session-id" in cookie
    assert "HttpOnly" in cookie


async def test_callback_rejects_unknown_state(client, monkeypatch):
    store = _store()
    store.pop_pending.return_value = None
    monkeypatch.setattr(auth_router, "_session_store", store)

    response = await client.get("/api/auth/callback", params={"code": "abc", "state": "unknown"})

    assert response.status_code == 400


async def test_callback_rejects_a_failed_code_exchange(client, monkeypatch):
    openid = _logged_in(monkeypatch, {"sub": "u1"})
    openid.token.side_effect = RuntimeError("invalid_grant")

    response = await client.get("/api/auth/callback", params={"code": "bad", "state": "xyz"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Login failed"


async def test_callback_rejects_a_userinfo_without_subject(client, monkeypatch):
    _logged_in(monkeypatch, {"email": "a@b.c"})

    response = await client.get("/api/auth/callback", params={"code": "abc", "state": "xyz"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Could not resolve identity"


async def test_logout_clears_session_and_returns_keycloak_redirect_url(client, monkeypatch):
    store = _store()
    store.get_session.return_value = MagicMock(refresh_token="rt", id_token="idt")
    monkeypatch.setattr(auth_router, "_session_store", store)
    openid = MagicMock()
    monkeypatch.setattr(auth_router, "_keycloak_openid", openid)

    client.cookies.set(auth_router._keycloak_settings.SESSION_COOKIE_NAME, "session-id-123")
    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    query = parse_qs(urlparse(response.json()["redirectUrl"]).query)
    assert query["id_token_hint"] == ["idt"]
    assert query["post_logout_redirect_uri"] == [auth_router._keycloak_settings.FRONTEND_URL]
    openid.logout.assert_called_once_with("rt")
    store.delete_session.assert_called_once_with("session-id-123")


async def test_logout_survives_keycloak_being_down(client, monkeypatch):
    store = _store()
    store.get_session.return_value = MagicMock(refresh_token="rt", id_token=None)
    monkeypatch.setattr(auth_router, "_session_store", store)
    openid = MagicMock()
    openid.logout.side_effect = RuntimeError("down")
    monkeypatch.setattr(auth_router, "_keycloak_openid", openid)

    client.cookies.set(auth_router._keycloak_settings.SESSION_COOKIE_NAME, "s")
    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    store.delete_session.assert_called_once_with("s")


async def test_logout_without_a_session_still_succeeds(client, monkeypatch):
    store = _store()
    monkeypatch.setattr(auth_router, "_session_store", store)

    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    store.delete_session.assert_not_called()


async def test_me_returns_the_dev_identity_under_full_access_mode(client):
    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["user_id"] == "dev-user"
    assert response.json()["is_admin"] is True
    assert "access_token" not in response.json()
