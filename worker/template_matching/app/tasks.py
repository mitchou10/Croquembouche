from qdrant_client import QdrantClient

from app import config, embeddings, storage
from app.celery_app import celery_app
from app.index import TemplateIndex

_index: TemplateIndex | None = None


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
