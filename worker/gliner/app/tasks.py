import logging

from celery import Task

from app import backend, extract
from app.celery_app import celery_app
from app.consumption import measured

logger = logging.getLogger(__name__)

# The broker or the backend may not be there yet: try again, a few times, backing off.
_RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "retry_kwargs": {"max_retries": 4}}


@celery_app.task(name="gliner.ping")
def ping() -> str:
    return "pong"


class _ReportsFailure(Task):
    """A search that cannot be done, whatever was tried, ends as failed on the backend: it is not left running."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            backend.report(args[0]["run_id"], {"status": "failed"})
        except Exception:
            logger.exception("Could not tell the backend that the search of %s failed", args[0].get("run_id"))


@celery_app.task(name="gliner.find_entities", base=_ReportsFailure, **_RETRY)
def find_entities(message: dict) -> None:
    """Finds the entities that have no zone in the text the OCR read (`{run_id, pages, entities}`, see `extract.find`)
    and hands what it found back to the backend, with what the search consumed."""
    with measured(message["run_id"]) as used:
        found = extract.find(message["pages"], message["entities"])
    result = {"status": "done", "found": found}
    backend.report(message["run_id"], {**result, **({"consumption": used.value} if used.value else {})})
