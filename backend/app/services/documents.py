import json
import secrets
from dataclasses import asdict, dataclass

import pymupdf

from app.core import storage

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


@dataclass
class Document:
    id: str
    owner_id: str
    name: str
    content_type: str
    pages: int


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


def _key(document_id: str, name: str) -> str:
    return f"documents/{document_id}/{name}"


def save(owner_id: str, name: str, data: bytes) -> Document:
    """Keeps a document with, for a PDF, a screenshot of each of its pages: the pages are what the model is drawn on."""
    if not data:
        raise InvalidDocumentError("Ce fichier est vide.")
    if len(data) > MAX_BYTES:
        raise InvalidDocumentError(f"Ce fichier est trop lourd ({MAX_BYTES // (1024 * 1024)} Mo au maximum).")
    content_type = sniff_type(data)
    if content_type is None:
        raise InvalidDocumentError("Seuls les images (PNG, JPEG, WebP, GIF) et les PDF sont acceptés.")

    screenshots = _render_pdf(data) if content_type == "application/pdf" else []
    document = Document(
        id=secrets.token_urlsafe(16),
        owner_id=owner_id,
        name=name,
        content_type=content_type,
        pages=len(screenshots) or 1,
    )
    storage.put_object(_key(document.id, f"original.{_EXTENSIONS[content_type]}"), data, content_type)
    for number, screenshot in enumerate(screenshots, start=1):
        storage.put_object(_key(document.id, f"pages/{number}.png"), screenshot, "image/png")
    # Written last: a document without its description is one that was never completed.
    storage.put_object(_key(document.id, "meta.json"), json.dumps(asdict(document)).encode(), "application/json")
    return document


def find(document_id: str) -> Document:
    try:
        raw, _ = storage.get_object(_key(document_id, "meta.json"))
    except storage.ObjectNotFoundError as error:
        raise DocumentNotFoundError(document_id) from error
    return Document(**json.loads(raw))


def page(document: Document, number: int) -> tuple[bytes, str]:
    """The image of a page (from 1): the screenshot of a PDF's page, or the image itself."""
    if not 1 <= number <= document.pages:
        raise DocumentNotFoundError(f"{document.id}/{number}")
    if document.content_type == "application/pdf":
        return storage.get_object(_key(document.id, f"pages/{number}.png"))
    return storage.get_object(_key(document.id, f"original.{_EXTENSIONS[document.content_type]}"))


def delete(document: Document) -> None:
    storage.delete_prefix(_key(document.id, ""))
