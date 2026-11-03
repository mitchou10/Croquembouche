import logging

from celery import Task
from qdrant_client import QdrantClient

from app import backend, config, embeddings, storage
from app.celery_app import celery_app
from app.classify import PageClassifier
from app.index import TemplateIndex
from app.match import match_document as match

logger = logging.getLogger(__name__)

_index: TemplateIndex | None = None
_classifier: PageClassifier | None = None


def get_index() -> TemplateIndex:
    """The index of the catalogue, made on first use: a worker that never indexes never loads a model."""
    global _index
    if _index is None:
        _index = TemplateIndex(
            QdrantClient(url=config.QDRANT_URL),
            embeddings.get_embedder(),
            storage.get_bytes,
            config.collection_name(),
        )
    return _index


def get_classifier() -> PageClassifier:
    global _classifier
    if _classifier is None:
        _classifier = PageClassifier(
            QdrantClient(url=config.QDRANT_URL), embeddings.get_embedder(), config.collection_name()
        )
    return _classifier


# The store or the bucket may not be there yet when the first message comes: try again, a few times, backing off.
_RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "retry_kwargs": {"max_retries": 4}}


@celery_app.task(name="template_matching.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="template_matching.index_template", **_RETRY)
def index_template(template: dict) -> dict[str, int]:
    """Indexes the pages of a model's document and the zones of its entities (see `TemplateIndex.index`)."""
    return get_index().index(template)


@celery_app.task(name="template_matching.remove_template", **_RETRY)
def remove_template(template_id: str) -> None:
    get_index().remove(template_id)


@celery_app.task(name="template_matching.classify_pages", **_RETRY)
def classify_pages(template_ids: list[str], page_keys: list[str]) -> list[dict]:
    """What each page of a document (its images, by key in the store) is among the given models (see
    `PageClassifier.classify`)."""
    return get_classifier().classify(template_ids, [storage.get_bytes(key) for key in page_keys])


class _ReportsFailure(Task):
    """A run that cannot be matched, whatever was tried, ends as failed on the backend: it is not left running."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            backend.report(args[0]["run_id"], {"status": "failed"})
        except Exception:
            logger.exception("Could not tell the backend that the run %s failed", args[0].get("run_id"))


@celery_app.task(name="template_matching.match_document", base=_ReportsFailure, **_RETRY)
def match_document(message: dict) -> None:
    """Classifies the pages of a document tried on an analysis and finds the elements of its models in them (see
    `match.match_document`), then hands the result back to the backend, which keeps the runs."""
    backend.report(message["run_id"], match(get_classifier(), storage.get_bytes, message))
