from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.dependencies import Analyses
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisOut,
    ElementCreate,
    FileDecision,
    Review,
    RunOut,
    ViewsOut,
)
from app.services import documents
from app.services.analyses import ForbiddenError, InvalidError, NotFoundError

router = APIRouter(tags=["Analyses"])


async def _run(call):
    """The service's refusals, as the answers they are."""
    try:
        return await call
    except NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from error
    except ForbiddenError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except InvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("", summary="Every analysis: those the person cannot open are named only")
async def list_analyses(service: Analyses) -> list[AnalysisOut]:
    return await service.search()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Make an analysis; it starts with its first use")
async def create(body: AnalysisCreate, service: Analyses) -> AnalysisOut:
    return await _run(service.create(body))


@router.get("/{analysis_id}")
async def get(analysis_id: str, service: Analyses) -> AnalysisOut:
    return await _run(service.get(analysis_id))


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an analysis: its owner only")
async def delete(analysis_id: str, service: Analyses) -> None:
    await _run(service.delete(analysis_id))


@router.post("/{analysis_id}/views", summary="Count one more look at the page of the analysis")
async def register_view(analysis_id: str, service: Analyses) -> ViewsOut:
    return ViewsOut(views=await _run(service.register_view(analysis_id)))


@router.post("/{analysis_id}/runs", status_code=status.HTTP_201_CREATED, summary="Try the analysis on a document")
async def start_run(
    analysis_id: str,
    service: Analyses,
    file: Annotated[UploadFile, File()],
    keep_screenshot: Annotated[bool, Form(alias="keepScreenshot")] = False,
) -> RunOut:
    # One byte more than the limit is enough to know the file is too big, without reading all of it.
    data = await file.read(documents.MAX_BYTES + 1)
    return await _run(service.start_run(analysis_id, file.filename or "document", data, keep_screenshot))


@router.get("/{analysis_id}/runs/{run_id}", summary="What a use found: its own person's alone")
async def get_run(analysis_id: str, run_id: str, service: Analyses) -> RunOut:
    return await _run(service.get_run(analysis_id, run_id))


@router.post("/{analysis_id}/runs/{run_id}/cancel", summary="Stop a use that is running: its own person's alone")
async def cancel_run(analysis_id: str, run_id: str, service: Analyses) -> RunOut:
    return await _run(service.cancel_run(analysis_id, run_id))


@router.put("/{analysis_id}/runs/{run_id}/detections/{detection_id}/review", summary="Validate, invalidate or annotate")
async def review_detection(analysis_id: str, run_id: str, detection_id: str, body: Review, service: Analyses) -> RunOut:
    return await _run(service.review_detection(analysis_id, run_id, detection_id, body))


@router.put(
    "/{analysis_id}/runs/{run_id}/pages/{page}/review", summary="Decide of the classification of a page of the document"
)
async def review_page(analysis_id: str, run_id: str, page: int, body: Review, service: Analyses) -> RunOut:
    return await _run(service.review_page(analysis_id, run_id, page, body))


@router.post("/{analysis_id}/runs/{run_id}/elements", status_code=status.HTTP_201_CREATED, summary="Add an element")
async def add_element(analysis_id: str, run_id: str, body: ElementCreate, service: Analyses) -> RunOut:
    return await _run(service.add_element(analysis_id, run_id, body))


@router.delete("/{analysis_id}/runs/{run_id}/elements/{detection_id}", summary="Take away an element added by hand")
async def remove_element(analysis_id: str, run_id: str, detection_id: str, service: Analyses) -> RunOut:
    return await _run(service.remove_element(analysis_id, run_id, detection_id))


@router.put("/{analysis_id}/runs/{run_id}/file", summary="Keep the screenshots of the document tried, or delete them")
async def decide_file(analysis_id: str, run_id: str, body: FileDecision, service: Analyses) -> RunOut:
    return await _run(service.decide_file(analysis_id, run_id, body.decision))
