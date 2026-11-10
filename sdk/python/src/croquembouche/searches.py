from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence

from ._call import UNSET, Caller, Document, file_of
from ._generated.api.searches import delete, get, list_searches, start
from ._generated.models import BodyStartApiSearchesPost, SearchOut, SearchSummaryOut
from .errors import WaitTimeoutError


class Search:
    """A search for the pages of the catalogue that look like the pages of a document: it runs on the server."""

    def __init__(self, searches: Searches, data: SearchOut) -> None:
        self._searches = searches
        self.data = data

    @property
    def id(self) -> str:
        return self.data.id

    @property
    def status(self) -> str:
        return self.data.status.value

    async def refresh(self) -> SearchOut:
        self.data = await self._searches.get(self.id)
        return self.data

    async def wait(self, *, timeout: float | None = 300, interval: float = 1.0) -> SearchOut:
        """Waits for the search to end, and gives it: its `neighbours` (the pages that look like those of the document,
        the likeliest first) and the `links` between them. Raises `WaitTimeoutError` after `timeout` seconds."""
        started = time.monotonic()
        while True:
            await self.refresh()
            if self.status != "running":
                return self.data
            if timeout is not None and time.monotonic() - started >= timeout:
                raise WaitTimeoutError(f"The search {self.id} was still running after {timeout} seconds.")
            await asyncio.sleep(interval)


class Searches:
    def __init__(self, call: Caller) -> None:
        self._call = call

    async def start(
        self, document: Document, *, k: int = 5, template_ids: Sequence[str] | None = None, filename: str | None = None
    ) -> Search:
        """Looks for the pages of the catalogue like those of a document: `k` neighbours for each page, among the models
        asked for or among every one the token can use."""
        body = BodyStartApiSearchesPost(
            file=file_of(document, filename), k=k, template_ids=list(template_ids) if template_ids else UNSET
        )
        return Search(self, await self._call(start, body=body))

    async def get(self, search_id: str) -> SearchOut:
        return await self._call(get, search_id)

    async def list(self) -> list[SearchSummaryOut]:
        """The searches of the token."""
        return await self._call(list_searches)

    async def delete(self, search_id: str) -> None:
        await self._call(delete, search_id)
