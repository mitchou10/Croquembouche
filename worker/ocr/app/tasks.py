import logging

from celery import Task

from app import backend, ocr, storage
from app.celery_app import celery_app
from app.consumption import measured

logger = logging.getLogger(__name__)

# The store may not be there yet when the first message comes: try again, a few times, backing off.
_RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "retry_kwargs": {"max_retries": 4}}


@celery_app.task(name="ocr.ping")
def ping() -> str:
    return "pong"


class _ReportsFailure(Task):
    """A reading that cannot be done, whatever was tried, ends as failed on the backend: it is not left running."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            backend.report(args[0]["run_id"], {"status": "failed"})
        except Exception:
            logger.exception("Could not tell the backend that the reading of %s failed", args[0].get("run_id"))


@celery_app.task(name="ocr.read_document", base=_ReportsFailure, **_RETRY)
def read_document(message: dict) -> None:
    """Reads the pages of a document tried on an analysis (`{run_id, page_keys}`, the images by key in the store; see
    `ocr.read`) and hands the text back to the backend. It runs beside the matching and nothing waits for it."""
    with measured(message["run_id"]) as used:
        pages = [
            {"page": number, **ocr.read(storage.get_bytes(key))} for number, key in enumerate(message["page_keys"], 1)
        ]
    backend.report(
        message["run_id"], {"status": "done", "pages": pages, **({"consumption": used.value} if used.value else {})}
    )
