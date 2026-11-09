from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.dependencies import Searches
from app.schemas.search import DEFAULT_NEIGHBOURS, SearchOut, SearchSummaryOut
from app.services import documents
from app.services.catalogue import InvalidError, NotFoundError

router = APIRouter(tags=["Searches"])


async def _run(call):
    """The service's refusals, as the answers they are."""
    try:
        return await call
    except NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from error
    except InvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Look for the pages of the catalogue that look like a document: running at first, a worker computes",
)
async def start(
    service: Searches,
    file: Annotated[UploadFile, File()],
    k: Annotated[int, Form()] = DEFAULT_NEIGHBOURS,
    template_ids: Annotated[list[str] | None, Form(alias="templateIds")] = None,
) -> SearchOut:
    # One byte more than the limit is enough to know the file is too big, without reading all of it.
    data = await file.read(documents.MAX_BYTES + 1)
    return await _run(service.start(file.filename or "document", data, k, template_ids))


@router.get("", summary="The searches of the person, the newest first")
async def list_searches(service: Searches) -> list[SearchSummaryOut]:
    return await service.mine()


@router.get("/{search_id}", summary="What a search found: its own person's alone")
async def get(search_id: str, service: Searches) -> SearchOut:
    return await _run(service.get(search_id))


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a search and its document")
async def delete(search_id: str, service: Searches) -> None:
    await _run(service.delete(search_id))


@router.get("/{search_id}/pages/{number}", summary="The image of a page (from 1) of the document that was sent")
async def get_page(search_id: str, number: int, service: Searches) -> Response:
    data, content_type = await _run(service.page(search_id, number))
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})
