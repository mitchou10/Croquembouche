"""Telling the worker what the catalogue is made of, so that it keeps its index of it (see worker/template_matching).

Indexing is a favour to the matching, not part of saving a model: it is asked for after the model is saved, and if the
broker cannot be reached the model is saved all the same (a later change indexes it again)."""

import logging
from typing import Protocol

from app.config import RedisSettings
from app.core.worker import QUEUE, make_client

logger = logging.getLogger(__name__)

# The names the worker gives its tasks.
INDEX_TASK = "template_matching.index_template"
REMOVE_TASK = "template_matching.remove_template"


class TemplateIndexer(Protocol):
    def index(self, message: dict) -> None: ...

    def remove(self, template_id: str) -> None: ...


class CeleryIndexer:
    def __init__(self, broker_url: str) -> None:
        self._app = make_client(broker_url)

    def _send(self, task: str, argument) -> None:
        try:
            self._app.send_task(task, args=[argument], queue=QUEUE)
        except Exception:
            logger.warning("Could not ask the worker to run %s", task, exc_info=True)

    def index(self, message: dict) -> None:
        self._send(INDEX_TASK, message)

    def remove(self, template_id: str) -> None:
        self._send(REMOVE_TASK, template_id)


_indexer: TemplateIndexer | None = None


def get_indexer() -> TemplateIndexer:
    global _indexer
    if _indexer is None:
        _indexer = CeleryIndexer(RedisSettings().REDIS_URL)
    return _indexer
