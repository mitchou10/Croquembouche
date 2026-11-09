import logging

from celery import Task
from qdrant_client import QdrantClient

from app import backend, config, embeddings, storage
from app.celery_app import celery_app
from app.classify import PageClassifier
from app.consumption import measured
from app.index import TemplateIndex
from app.match import match_document as match
from app.neighbours import NeighbourSearch

logger = logging.getLogger(__name__)

_index: TemplateIndex | None = None
_classifier: PageClassifier | None = None
_searcher: NeighbourSearch | None = None


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


def get_searcher() -> NeighbourSearch:
    global _searcher
    if _searcher is None:
        _searcher = NeighbourSearch(
            QdrantClient(url=config.QDRANT_URL), embeddings.get_embedder(), config.collection_name()
        )
    return _searcher


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


@celery_app.task(name="template_matching.drop_old_indexes", **_RETRY)
def drop_old_indexes() -> dict:
    """Deletes the indexes of the embedding models that are not the current one (see `TemplateIndex`)."""
    done = get_index().drop_old_collections(config.QDRANT_COLLECTION)
    if "refused" in done:
        logger.warning(
            "The old indexes are kept: the index of %s is empty, index the catalogue again first",
            config.collection_name(),
        )
    else:
        logger.info("Old indexes deleted: %s", ", ".join(done["deleted"]) or "none")
    return done


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
    with measured(message["run_id"]) as used:
        result = match(get_classifier(), storage.get_bytes, message)
    # What it consumed goes with the answer, when it could be measured.
    backend.report(message["run_id"], {**result, **({"consumption": used.value} if used.value else {})})


class _ReportsSearchFailure(Task):
    """A search that cannot be made, whatever was tried, ends as failed on the backend: it is not left running."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            backend.report_search(args[0]["search_id"], {"status": "failed"})
        except Exception:
            logger.exception("Could not tell the backend that the search %s failed", args[0].get("search_id"))


@celery_app.task(name="template_matching.find_neighbours", base=_ReportsSearchFailure, **_RETRY)
def find_neighbours(message: dict) -> None:
    """Looks for the pages of the catalogue that look like the pages of a document (`message` is `{search_id,
    page_keys, k, template_ids}`: the images by key in the store, how many neighbours each page asks for, and the models
    to look in, or none for every one), then hands the result and what it consumed back to the backend, which keeps the
    searches (see `NeighbourSearch.search`)."""
    with measured(message["search_id"]) as used:
        result = get_searcher().search(
            [storage.get_bytes(key) for key in message["page_keys"]], message["k"], message.get("template_ids")
        )
    backend.report_search(message["search_id"], {**result, **({"consumption": used.value} if used.value else {})})
