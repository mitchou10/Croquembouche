import uuid
from dataclasses import dataclass
from urllib.parse import quote

import pymupdf
from starlette.concurrency import run_in_threadpool

from app.core import storage
from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.services import pdf_zones

# What is kept is ranged by kind, then by owner, so that everything a person sent to be analysed is under one prefix (to
# purge it, to expire it). `ANALYSES`: what is sent to be analysed (a use of an analysis, a search). `MODELS`: the
# example documents of the models, which other people use too: a purge of what a person sent does not take them.
ANALYSES = "analyses"
MODELS = "models"

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


@dataclass
class Prepared:
    """A file looked at: what it is, and the screenshots of its pages if it is a PDF."""

    content_type: str
    screenshots: list[bytes]

    def pages(self, data: bytes) -> list[bytes]:
        """The image of each page: the screenshots of a PDF, or the image itself."""
        return self.screenshots or [data]


def _prepare(data: bytes) -> Prepared:
    """What a file is, and the screenshots of its pages if it is a PDF; refuses what cannot be kept."""
    if not data:
        raise InvalidDocumentError("Ce fichier est vide.")
    if len(data) > MAX_BYTES:
        raise InvalidDocumentError(f"Ce fichier est trop lourd ({MAX_BYTES // (1024 * 1024)} Mo au maximum).")
    content_type = sniff_type(data)
    if content_type is None:
        raise InvalidDocumentError("Seuls les images (PNG, JPEG, WebP, GIF) et les PDF sont acceptés.")
    return Prepared(content_type, _render_pdf(data) if content_type == "application/pdf" else [])


def _store(document: Document, data: bytes, screenshots: list[bytes]) -> None:
    storage.put_object(_key(document, f"original.{_EXTENSIONS[document.content_type]}"), data, document.content_type)
    for number, screenshot in enumerate(screenshots, start=1):
        storage.put_object(_key(document, f"pages/{number}.png"), screenshot, "image/png")


async def prepare(data: bytes) -> Prepared:
    """Looks at a file without keeping it; refuses what cannot be kept. Reading a PDF blocks: off the event loop."""
    return await run_in_threadpool(_prepare, data)


def owner_prefix(kind: str, owner_id: str) -> str:
    """Where what a person sent of a kind is in the store: `analyses/<id>/`. The identifier (the one of their account,
    never their address or name) is encoded for a key, and the prefix ends with the slash: `bob` is not `bobby`."""
    return f"{kind}/{quote(owner_id, safe='')}/"


async def save(
    repository: DocumentRepository,
    owner_id: str,
    name: str,
    data: bytes,
    prepared: Prepared | None = None,
    *,
    kind: str,
) -> Document:
    """Keeps a document with, for a PDF, a screenshot of each of its pages: the pages are what the model is drawn on.
    Reading a PDF and talking to the store block: they run off the event loop. `prepared` spares looking at it twice.
    `kind`: `ANALYSES` or `MODELS`, where it is kept (see `owner_prefix`)."""
    prepared = prepared or await prepare(data)
    content_type, screenshots = prepared.content_type, prepared.screenshots
    identifier = uuid.uuid4()
    document = Document(
        id=identifier,
        owner_id=owner_id,
        name=name[:255],
        content_type=content_type,
        pages=len(screenshots) or 1,
        storage_prefix=f"{owner_prefix(kind, owner_id)}{identifier}/",
    )
    await run_in_threadpool(_store, document, data, screenshots)
    # Recorded last: a document the database does not know is one that was never completed.
    await repository.add(document)
    return document


def page_key(document: Document, number: int) -> str:
    """Where the image of a page (from 1) is in the store: the screenshot of a PDF's page, or the image itself."""
    if document.content_type == "application/pdf":
        return _key(document, f"pages/{number}.png")
    return _key(document, f"original.{_EXTENSIONS[document.content_type]}")


async def page(document: Document, number: int) -> tuple[bytes, str]:
    """The image of a page (from 1): the screenshot of a PDF's page, or the image itself."""
    if not 1 <= number <= document.pages:
        raise DocumentNotFoundError(f"{document.id}/{number}")
    return await run_in_threadpool(storage.get_object, page_key(document, number))


async def delete(repository: DocumentRepository, document: Document) -> None:
    await run_in_threadpool(storage.delete_prefix, document.storage_prefix)
    await repository.delete(document)


async def suggest_zones(document: Document) -> list[pdf_zones.Suggestion]:
    """The entities a PDF suggests by itself (see `pdf_zones`); none for an image, which has no fields and no text."""
    if document.content_type != "application/pdf":
        return []
    data, _ = await run_in_threadpool(
        storage.get_object, _key(document, f"original.{_EXTENSIONS[document.content_type]}")
    )
    return await run_in_threadpool(pdf_zones.suggest, data)
