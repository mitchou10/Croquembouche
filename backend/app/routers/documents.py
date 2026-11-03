from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.core.security.factory import RequestContext, get_current_user
from app.services import documents

router = APIRouter(tags=["Documents"])

CurrentUser = Annotated[RequestContext, Depends(get_current_user)]


def _own(document_id: str, user: RequestContext) -> documents.Document:
    """A document is its owner's (and an administrator's): anyone else is told it does not exist."""
    try:
        document = documents.find(document_id)
    except documents.DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found") from error
    if document.owner_id != user.user_id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


# Plain `def`: reading a PDF and rendering its pages is CPU-bound and must not hold the event loop.
@router.post("", status_code=status.HTTP_201_CREATED, summary="Upload an image or a PDF")
def upload(user: CurrentUser, file: Annotated[UploadFile, File()]) -> dict:
    # One byte more than the limit is enough to know the file is too big, without reading all of it.
    data = file.file.read(documents.MAX_BYTES + 1)
    try:
        document = documents.save(user.user_id, file.filename or "document", data)
    except documents.InvalidDocumentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return {key: value for key, value in asdict(document).items() if key != "owner_id"}


@router.get("/{document_id}/pages/{number}", summary="The image of a page (from 1)")
def get_page(document_id: str, number: int, user: CurrentUser) -> Response:
    document = _own(document_id, user)
    try:
        data, content_type = documents.page(document, number)
    except documents.DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found") from error
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document")
def delete(document_id: str, user: CurrentUser) -> None:
    documents.delete(_own(document_id, user))
