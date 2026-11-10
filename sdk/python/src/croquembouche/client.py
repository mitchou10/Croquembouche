import httpx2

from ._call import Caller
from ._generated.client import AuthenticatedClient
from .analyses import Analyses
from .auth import BearerToken, ClientCredentials
from .searches import Searches
from .tasks import Tasks
from .templates import Templates
from .users import Users


class Croquembouche:
    """A client of the API, to be used in `async with`::

        async with Croquembouche(url, token_url=..., client_id=..., client_secret=...) as client:
            form = await client.templates.get(template_id)
            run = await client.analyses.run(analysis_id, "scan.pdf")
            result = await run.wait()

    How it signs in, from the least to the most to say: nothing (a backend that asks for nothing), `token` (one the
    program has), `token_url` with `client_id` and `client_secret` (a service account, which gets its own token and
    renews it), or `auth=` with any of `croquembouche.auth` (an exchanged token, for instance).
    """

    def __init__(
        self,
        url: str,
        *,
        auth: httpx2.Auth | None = None,
        token: str | None = None,
        token_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        if auth is None:
            if token is not None:
                auth = BearerToken(token)
            elif token_url or client_id or client_secret:
                if not (token_url and client_id and client_secret):
                    raise ValueError("A service account needs token_url, client_id and client_secret together.")
                auth = ClientCredentials(token_url, client_id, client_secret, transport=transport)
        self._http = httpx2.AsyncClient(base_url=url, auth=auth, timeout=timeout, transport=transport)
        generated = AuthenticatedClient(base_url=url, token="", timeout=httpx2.Timeout(timeout))
        generated.set_async_httpx_client(self._http)
        caller = Caller(generated)
        self.templates = Templates(caller)
        self.analyses = Analyses(caller)
        self.searches = Searches(caller)
        self.tasks = Tasks(caller)
        self.users = Users(caller)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "Croquembouche":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
