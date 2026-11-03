import uuid

import pymupdf
from starlette.concurrency import run_in_threadpool

from app.core import storage
from app.models.document import Document
from app.repositories.document import DocumentRepository

MAX_BYTES = 20 * 1024 * 1024
# A page is rendered whole as an image: more pages than this is a book, not an example of a model.
MAX_PAGES = 30
# 2 = 144 dpi: sharp enough to draw a zone on and to match against, without weighing a lot.
RENDER_ZOOM = 2

# What a file begins with, and the type it is then: the name and the type the browser sent are the sender's word.
_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
)
_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


class InvalidDocumentError(Exception):
    """The file is not a document that can be kept; the message says why, for the person who sent it."""


class DocumentNotFoundError(Exception):
    pass


def sniff_type(data: bytes) -> str | None:
    for signature, content_type in _SIGNATURES:
        if data.startswith(signature):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _render_pdf(data: bytes) -> list[bytes]:
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception as error:
        raise InvalidDocumentError("Ce PDF est illisible.") from error
    with pdf:
        if pdf.needs_pass:
            raise InvalidDocumentError("Ce PDF est protégé par un mot de passe.")
        if pdf.page_count == 0:
            raise InvalidDocumentError("Ce PDF n’a aucune page.")
        if pdf.page_count > MAX_PAGES:
            raise InvalidDocumentError(f"Ce PDF a trop de pages ({MAX_PAGES} au maximum).")
        matrix = pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        return [page.get_pixmap(matrix=matrix, alpha=False).tobytes("png") for page in pdf]


def _key(document: Document, name: str) -> str:
    return f"{document.storage_prefix}{name}"


def _prepare(data: bytes) -> tuple[str, list[bytes]]:
    """What a file is, and the screenshots of its pages if it is a PDF; refuses what cannot be kept."""
    if not data:
        raise InvalidDocumentError("Ce fichier est vide.")
    if len(data) > MAX_BYTES:
        raise InvalidDocumentError(f"Ce fichier est trop lourd ({MAX_BYTES // (1024 * 1024)} Mo au maximum).")
    content_type = sniff_type(data)
    if content_type is None:
        raise InvalidDocumentError("Seuls les images (PNG, JPEG, WebP, GIF) et les PDF sont acceptés.")
    return content_type, _render_pdf(data) if content_type == "application/pdf" else []


def _store(document: Document, data: bytes, screenshots: list[bytes]) -> None:
    storage.put_object(_key(document, f"original.{_EXTENSIONS[document.content_type]}"), data, document.content_type)
    for number, screenshot in enumerate(screenshots, start=1):
        storage.put_object(_key(document, f"pages/{number}.png"), screenshot, "image/png")


async def save(repository: DocumentRepository, owner_id: str, name: str, data: bytes) -> Document:
    """Keeps a document with, for a PDF, a screenshot of each of its pages: the pages are what the model is drawn on.
    Reading a PDF and talking to the store block: they run off the event loop."""
    content_type, screenshots = await run_in_threadpool(_prepare, data)
    identifier = uuid.uuid4()
    document = Document(
        id=identifier,
        owner_id=owner_id,
        name=name[:255],
        content_type=content_type,
        pages=len(screenshots) or 1,
        storage_prefix=f"documents/{identifier}/",
    )
    await run_in_threadpool(_store, document, data, screenshots)
    # Recorded last: a document the database does not know is one that was never completed.
    await repository.add(document)
    return document


async def page(document: Document, number: int) -> tuple[bytes, str]:
    """The image of a page (from 1): the screenshot of a PDF's page, or the image itself."""
    if not 1 <= number <= document.pages:
        raise DocumentNotFoundError(f"{document.id}/{number}")
    if document.content_type == "application/pdf":
        return await run_in_threadpool(storage.get_object, _key(document, f"pages/{number}.png"))
    return await run_in_threadpool(storage.get_object, _key(document, f"original.{_EXTENSIONS[document.content_type]}"))


async def delete(repository: DocumentRepository, document: Document) -> None:
    await run_in_threadpool(storage.delete_prefix, document.storage_prefix)
    await repository.delete(document)
