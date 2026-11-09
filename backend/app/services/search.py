"""Searching for the documents that look like one that was sent: it is asked of the worker (which has the index of the
catalogue and does all the computing) and answered by it; the backend keeps the document, what was found and what it
consumed, for the person who searched alone."""

import logging
import uuid

from starlette.concurrency import run_in_threadpool

from app.core.matching import MatchingDispatcher
from app.core.security.factory import RequestContext
from app.models.search import Search
from app.repositories.catalogue import CatalogueRepository
from app.repositories.document import DocumentRepository
from app.repositories.search import SearchRepository
from app.schemas.matching import SearchResult
from app.schemas.search import MAX_NEIGHBOURS, LinkOut, NeighbourOut, SearchOut, SearchSummaryOut
from app.services import documents
from app.services.catalogue import InvalidError, NotFoundError
from app.services.consumption import consumed

logger = logging.getLogger(__name__)


def page_node(page: int) -> str:
    """How a page of the document is called in the links of a search."""
    return f"page-{page}"


def _consumption(search: Search):
    return (
        None if search.energy_kwh is None else consumed(search.energy_kwh, search.co2_kg or 0, search.duration_s or 0)
    )


def _summary(search: Search) -> dict:
    document = search.document
    return {
        "id": str(search.id),
        "file_name": document.name if document else "document",
        "status": search.status,
        "k": search.k,
        "template_ids": search.template_ids,
        "created_at": search.created_at,
        "pages": document.pages if document else 0,
        "neighbour_count": len(search.neighbours),
        "consumption": _consumption(search),
    }


def summary_of(search: Search) -> SearchSummaryOut:
    return SearchSummaryOut(**_summary(search))


def view_of(search: Search) -> SearchOut:
    return SearchOut(
        **_summary(search),
        neighbours=[NeighbourOut(**n) for n in search.neighbours],
        links=[LinkOut(**link) for link in search.links],
    )


def finish(search: Search, result: SearchResult) -> None:
    """Records how a search that was running went. The caller commits. Neighbours are one node whatever the pages of the
    document they look like (the best of their similarities is kept); a link to a node that is not there is dropped."""
    search.status = result.status
    if result.consumption is not None:
        search.energy_kwh = result.consumption.energy_kwh
        search.co2_kg = result.consumption.co2_kg
        search.duration_s = result.consumption.duration_s
    if result.status != "done":
        return
    best: dict[str, dict] = {}
    for n in result.neighbours:
        node = f"{n.template_id}:{n.template_page}"
        if node not in best or n.similarity > best[node]["similarity"]:
            best[node] = {
                "id": node,
                "template_id": n.template_id,
                "template_page": n.template_page,
                "document_id": n.document_id,
                "similarity": n.similarity,
            }
    pages = search.document.pages if search.document else 0
    known = {page_node(p) for p in range(1, pages + 1)} | set(best)
    search.neighbours = sorted(best.values(), key=lambda n: (-n["similarity"], n["id"]))
    search.links = [
        {"source": link.source, "target": link.target, "similarity": link.similarity}
        for link in result.links
        if link.source in known and link.target in known and link.source != link.target
    ]


async def apply(repository: SearchRepository, search_id: str, result: SearchResult) -> bool:
    """What the worker handed back. False when there is no such search running: one that already ended (or was deleted)
    is left as it is."""
    search = await repository.get(search_id)
    if search is None or search.status != "running":
        return False
    finish(search, result)
    await repository.commit()
    return True


async def expire(repository: SearchRepository, seconds: int) -> None:
    """Ends as failed the searches the worker never answered for, not left running."""
    stale = await repository.stale(seconds)
    for search in stale:
        finish(search, SearchResult(status="failed"))
    if stale:
        await repository.commit()


class SearchService:
    def __init__(
        self,
        repository: SearchRepository,
        documents_repository: DocumentRepository,
        catalogue: CatalogueRepository,
        dispatcher: MatchingDispatcher,
        user: RequestContext,
        timeout_seconds: int,
    ) -> None:
        self._repository = repository
        self._documents = documents_repository
        self._catalogue = catalogue
        self._dispatcher = dispatcher
        self._user = user
        self._timeout = timeout_seconds

    async def _own(self, search_id: str) -> Search:
        """A search is its person's alone, an administrator included: anyone else is told it does not exist."""
        await expire(self._repository, self._timeout)
        search = await self._repository.get(search_id)
        if search is None or search.user_id != self._user.user_id:
            raise NotFoundError(search_id)
        return search

    async def mine(self) -> list[SearchSummaryOut]:
        await expire(self._repository, self._timeout)
        return [summary_of(s) for s in await self._repository.of_user(self._user.user_id)]

    async def get(self, search_id: str) -> SearchOut:
        return view_of(await self._own(search_id))

    async def start(self, file_name: str, data: bytes, k: int, template_ids: list[str] | None) -> SearchOut:
        """Looks for the pages of the catalogue that look like the pages of a document, in the models given or in every
        one (the catalogue is everyone's). It answers at once, running: the worker computes."""
        if not 1 <= k <= MAX_NEIGHBOURS:
            raise InvalidError(f"Le nombre de voisins est compris entre 1 et {MAX_NEIGHBOURS}.")
        wanted = list(dict.fromkeys(template_ids)) if template_ids else None
        for template_id in wanted or []:
            if await self._catalogue.get_template(template_id) is None:
                raise InvalidError("Un des modèles choisis n’existe pas.")
        try:
            prepared = await documents.prepare(data)
        except documents.InvalidDocumentError as error:
            raise InvalidError(str(error)) from error
        saved = await documents.save(self._documents, self._user.user_id, file_name, data, prepared)
        search = Search(
            id=uuid.uuid4(),
            user_id=self._user.user_id,
            document_id=saved.id,
            status="running",
            k=k,
            template_ids=wanted,
        )
        self._repository.add(search)
        await self._repository.commit()
        # Only after the search is recorded: the worker's answer is about a search that exists.
        message = {
            "search_id": str(search.id),
            "page_keys": [documents.page_key(saved, number) for number in range(1, saved.pages + 1)],
            "k": k,
            "template_ids": wanted,
        }
        try:
            await run_in_threadpool(self._dispatcher.dispatch_search, message)
        except Exception:
            logger.warning("Could not ask the worker to search %s", search.id, exc_info=True)
            finish(search, SearchResult(status="failed"))
            await self._repository.commit()
        return view_of(search)

    async def delete(self, search_id: str) -> None:
        """Deletes a search, with the document that was sent and its pages."""
        search = await self._own(search_id)
        document = search.document
        if search.status == "running":
            try:
                await run_in_threadpool(self._dispatcher.revoke_search, str(search.id))
            except Exception:
                logger.warning("Could not ask the worker to stop the search %s", search.id, exc_info=True)
        await self._repository.delete(search)
        await self._repository.commit()
        if document is not None:
            await documents.delete(self._documents, document)

    async def page(self, search_id: str, number: int) -> tuple[bytes, str]:
        """The image of a page (from 1) of the document that was sent."""
        search = await self._own(search_id)
        if search.document is None:
            raise NotFoundError(search_id)
        try:
            return await documents.page(search.document, number)
        except documents.DocumentNotFoundError as error:
            raise NotFoundError(f"{search_id}/{number}") from error
