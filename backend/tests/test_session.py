import json
import time
from unittest.mock import MagicMock

import fakeredis
import pytest

from app.core.security.session import PendingAuth, SessionStore

TOKENS = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "id_token": "idt"}


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def openid():
    return MagicMock()


@pytest.fixture
def store(redis, openid):
    return SessionStore(redis, openid, ttl_seconds=600)


def test_a_pending_login_can_only_be_popped_once(store):
    store.save_pending("state", PendingAuth(code_verifier="v", next_path="/x"))

    assert store.pop_pending("state") == PendingAuth(code_verifier="v", next_path="/x")
    assert store.pop_pending("state") is None


def test_a_session_is_read_back_while_the_token_is_valid(store, openid):
    session_id = store.create_session({"user_id": "u1"}, TOKENS)

    session = store.get_session(session_id)

    assert session.identity == {"user_id": "u1"} and session.id_token == "idt"
    openid.refresh_token.assert_not_called()


def test_an_unknown_session_is_none(store):
    assert store.get_session("nope") is None


def _expire(redis, session_id):
    key = f"croquembouche:auth:session:{session_id}"
    data = json.loads(redis.get(key))
    data["expires_at"] = time.time() + 5
    redis.set(key, json.dumps(data))


def test_a_token_about_to_expire_is_refreshed(store, redis, openid):
    openid.refresh_token.return_value = {"access_token": "at2", "refresh_token": "rt2", "expires_in": 3600}
    session_id = store.create_session({"user_id": "u1"}, TOKENS)
    _expire(redis, session_id)

    session = store.get_session(session_id)

    assert session.access_token == "at2" and session.refresh_token == "rt2"
    assert session.id_token == "idt"
    assert store.get_session(session_id).access_token == "at2"


def test_a_refused_refresh_ends_the_session(store, redis, openid):
    openid.refresh_token.side_effect = RuntimeError("expired")
    session_id = store.create_session({"user_id": "u1"}, TOKENS)
    _expire(redis, session_id)

    assert store.get_session(session_id) is None
    assert store.get_session(session_id) is None
    assert redis.keys("croquembouche:auth:session:*") == []


def test_delete_session(store):
    session_id = store.create_session({"user_id": "u1"}, TOKENS)

    store.delete_session(session_id)

    assert store.get_session(session_id) is None


def test_rate_limit_allows_up_to_the_limit(store):
    results = [store.check_rate_limit("ip", 2, 60) for _ in range(3)]

    assert results == [True, True, False]
