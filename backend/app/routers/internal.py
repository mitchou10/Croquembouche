"""What only the worker calls: it hands back the result of a use. Not under /api, so the frontend never forwards to it;
and it asks for the key the worker and the backend share."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import MatchingSettings
from app.dependencies import Db
from app.repositories.analysis import AnalysisRepository
from app.repositories.document import DocumentRepository
from app.schemas.matching import MatchingResult
from app.services import matching_results


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
