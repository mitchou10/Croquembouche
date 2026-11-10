import httpx2
import pytest

from croquembouche import AuthenticationError, BearerToken, ClientCredentials, Croquembouche, TokenExchange, token_url
from croquembouche.auth import ACCESS_TOKEN, TOKEN_EXCHANGE

from .conftest import URL, template

TOKEN_URL = "http://keycloak.test/realms/r/protocol/openid-connect/token"


class Keycloak:
    """A token endpoint: a new token each time it is asked, valid for `expires_in` seconds."""

    def __init__(self, expires_in=300, status=200) -> None:
        self.asked: list[dict[str, str]] = []
        self.expires_in, self.status = expires_in, status

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        form = dict(httpx2.QueryParams(request.content.decode()))
        self.asked.append(form)
        if self.status >= 400:
            return httpx2.Response(self.status, json={"error": "invalid_client", "error_description": "Bad secret"})
        return httpx2.Response(200, json={"access_token": f"token-{len(self.asked)}", "expires_in": self.expires_in})


class Both:
    """Keycloak and the API behind one transport, and what the API saw as `Authorization`."""

    def __init__(self, keycloak: Keycloak, revoked: set[str] = frozenset()) -> None:
        self.keycloak, self.revoked, self.bearers = keycloak, revoked, []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return self.keycloak.handle(request)
        self.bearers.append(request.headers.get("authorization"))
        if request.headers.get("authorization", "").removeprefix("Bearer ") in self.revoked:
            return httpx2.Response(401, json={"detail": "Not authenticated"})
        return httpx2.Response(200, json=[template()])


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def service(both: Both, clock: Clock) -> Croquembouche:
    transport = httpx2.MockTransport(both)
    auth = ClientCredentials(TOKEN_URL, "mille-feuille", "secret", transport=transport, clock=clock)
    return Croquembouche(URL, auth=auth, transport=transport)


def test_the_token_endpoint_of_a_realm():
    assert token_url("http://kc/", "croquembouche") == "http://kc/realms/croquembouche/protocol/openid-connect/token"


async def test_a_service_account_gets_a_token_and_keeps_it_until_it_is_about_to_run_out():
    keycloak, clock = Keycloak(expires_in=300), Clock()
    both = Both(keycloak)
    async with service(both, clock) as client:
        await client.templates.list()
        await client.templates.list()
        assert both.bearers == ["Bearer token-1"] * 2 and len(keycloak.asked) == 1
        assert keycloak.asked[0] == {
            "grant_type": "client_credentials",
            "client_id": "mille-feuille",
            "client_secret": "secret",
        }

        clock.now += 269  # 300 seconds, less the 30 it is replaced before
        await client.templates.list()
        assert len(keycloak.asked) == 1
        clock.now += 2
        await client.templates.list()
        assert both.bearers[-1] == "Bearer token-2" and len(keycloak.asked) == 2


async def test_a_token_that_was_revoked_is_asked_for_again_once():
    keycloak, clock = Keycloak(), Clock()
    both = Both(keycloak, revoked={"token-1"})
    async with service(both, clock) as client:
        assert len(await client.templates.list()) == 1
        assert both.bearers == ["Bearer token-1", "Bearer token-2"]


async def test_keycloak_refusing_is_an_authentication_error_with_its_reason():
    both = Both(Keycloak(status=401))
    async with service(both, Clock()) as client:
        with pytest.raises(AuthenticationError) as error:
            await client.templates.list()
    assert error.value.detail == "Bad secret" and both.bearers == []


async def test_a_token_exchanged_for_croquembouche_is_asked_with_the_token_of_the_person():
    keycloak, clock = Keycloak(), Clock()
    both = Both(keycloak)
    transport = httpx2.MockTransport(both)
    people = iter(["julie-1", "julie-2"])
    auth = TokenExchange(TOKEN_URL, "mille-feuille", "secret", lambda: next(people), transport=transport, clock=clock)
    async with Croquembouche(URL, auth=auth, transport=transport) as client:
        await client.templates.list()
        clock.now += 1000
        await client.templates.list()

    assert keycloak.asked[0] == {
        "grant_type": TOKEN_EXCHANGE,
        "client_id": "mille-feuille",
        "client_secret": "secret",
        "subject_token": "julie-1",
        "subject_token_type": ACCESS_TOKEN,
        "requested_token_type": ACCESS_TOKEN,
        "audience": "croquembouche-backend",
    }
    assert keycloak.asked[1]["subject_token"] == "julie-2"  # the person's current token, asked for again


async def test_a_token_the_program_has_is_sent_as_it_is_or_as_its_function_gives_it():
    both = Both(Keycloak())
    transport = httpx2.MockTransport(both)
    async with Croquembouche(URL, token="abc", transport=transport) as client:
        await client.templates.list()
    async with Croquembouche(URL, auth=BearerToken(lambda: "from-a-function"), transport=transport) as client:
        await client.templates.list()
    assert both.bearers == ["Bearer abc", "Bearer from-a-function"]


async def test_the_service_account_can_be_given_as_plain_arguments():
    keycloak = Keycloak()
    both = Both(keycloak)
    transport = httpx2.MockTransport(both)
    async with Croquembouche(
        URL, token_url=TOKEN_URL, client_id="mille-feuille", client_secret="secret", transport=transport
    ) as client:
        await client.templates.list()
    assert both.bearers == ["Bearer token-1"]

    with pytest.raises(ValueError, match="together"):
        Croquembouche(URL, client_id="mille-feuille")


async def test_without_anything_to_sign_in_with_nothing_is_sent():
    both = Both(Keycloak())
    async with Croquembouche(URL, transport=httpx2.MockTransport(both)) as client:
        await client.templates.list()
    assert both.bearers == [None]
