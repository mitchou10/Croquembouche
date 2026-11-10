"""What only the worker calls: it hands back the result of a use. Not under /api, so the frontend never forwards to it;
and it asks for the key the worker and the backend share."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import MatchingSettings
from app.core.matching import MatchingDispatcher, get_dispatcher
from app.dependencies import Db, Tasks
from app.repositories.analysis import AnalysisRepository
from app.repositories.document import DocumentRepository
from app.repositories.search import SearchRepository
from app.schemas.matching import FindResult, MatchingResult, OcrResult, SearchResult
from app.schemas.worker import WorkerRegistration
from app.services import matching_results, search
from app.services.tasks import NotRegisteredError


def worker_only(x_internal_key: Annotated[str, Header()] = "") -> None:
    key = MatchingSettings().INTERNAL_API_KEY
    if not key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No key is set for the worker")
    if not hmac.compare_digest(x_internal_key.encode(), key.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not the worker")


router = APIRouter(tags=["Worker"], dependencies=[Depends(worker_only)], include_in_schema=False)


@router.post("/runs/{run_id}/result", status_code=status.HTTP_204_NO_CONTENT)
async def result(run_id: str, body: MatchingResult, db: Db) -> None:
    """How a use went, from the worker. One that already ended is left as it is."""
    if not await matching_results.apply(AnalysisRepository(db), DocumentRepository(db), run_id, body):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such use running")


@router.post("/runs/{run_id}/ocr", status_code=status.HTTP_204_NO_CONTENT)
async def ocr(
    run_id: str, body: OcrResult, db: Db, dispatcher: Annotated[MatchingDispatcher, Depends(get_dispatcher)]
) -> None:
    """The text of the document of a use, from the OCR worker, which reads beside the matching: it may come after the
    use is done."""
    if not await matching_results.apply_ocr(
        AnalysisRepository(db), DocumentRepository(db), run_id, body, dispatcher.dispatch_find
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such use being read")


@router.post("/runs/{run_id}/found", status_code=status.HTTP_204_NO_CONTENT)
async def found(run_id: str, body: FindResult, db: Db) -> None:
    """What the GLiNER worker found in the text for the entities with no zone: it comes after the text, so after the
    use is done."""
    if not await matching_results.apply_found(AnalysisRepository(db), run_id, body):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such use being searched")


@router.post("/searches/{search_id}/result", status_code=status.HTTP_204_NO_CONTENT)
async def search_result(search_id: str, body: SearchResult, db: Db) -> None:
    """How a search for similar documents went, from the worker. One that already ended is left as it is."""
    if not await search.apply(SearchRepository(db), search_id, body):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such search running")


@router.put("/workers/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def register(instance_id: str, body: WorkerRegistration, service: Tasks) -> None:
    """An instance of a worker starts (or declares its tasks again): the tasks it can be given, and the first sign
    that it is alive."""
    await service.register(instance_id, body)


@router.post("/workers/{instance_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def heartbeat(instance_id: str, service: Tasks) -> None:
    """An instance of a worker is alive. 404 when it is not known: it registers again."""
    try:
        await service.heartbeat(instance_id)
    except NotRegisteredError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such worker") from error


@router.delete("/workers/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister(instance_id: str, service: Tasks) -> None:
    """An instance of a worker stops: its tasks are no longer on offer."""
    await service.unregister(instance_id)
