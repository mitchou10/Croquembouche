from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.dependencies import CurrentUser, Db
from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.schemas.catalogue import DocumentOut
from app.services import documents

router = APIRouter(tags=["Documents"])


async def _own(repository: DocumentRepository, document_id: str, user: CurrentUser) -> Document:
    """A document is its owner's (and an administrator's): anyone else is told it does not exist."""
    document = await repository.get(document_id)
    if document is None or (document.owner_id != user.user_id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("", status_code=status.HTTP_201_CREATED, summary="Upload an image or a PDF")
async def upload(user: CurrentUser, db: Db, file: Annotated[UploadFile, File()]) -> DocumentOut:
    # One byte more than the limit is enough to know the file is too big, without reading all of it.
    data = await file.read(documents.MAX_BYTES + 1)
    try:
        document = await documents.save(DocumentRepository(db), user.user_id, file.filename or "document", data)
    except documents.InvalidDocumentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return DocumentOut(
        id=str(document.id), name=document.name, content_type=document.content_type, pages=document.pages
    )


@router.get("/{document_id}/pages/{number}", summary="The image of a page (from 1)")
async def get_page(document_id: str, number: int, user: CurrentUser, db: Db) -> Response:
    document = await _own(DocumentRepository(db), document_id, user)
    try:
        data, content_type = await documents.page(document, number)
    except documents.DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found") from error
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document")
async def delete(document_id: str, user: CurrentUser, db: Db) -> None:
    repository = DocumentRepository(db)
    await documents.delete(repository, await _own(repository, document_id, user))
