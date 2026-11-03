"""Telling the worker what the catalogue is made of, so that it keeps its index of it (see worker/template_matching).

Indexing is a favour to the matching, not part of saving a model: it is asked for after the model is saved, and if the
broker cannot be reached the model is saved all the same (a later change indexes it again)."""

import logging
from typing import Protocol

from celery import Celery

from app.config import RedisSettings

logger = logging.getLogger(__name__)

# The names the worker gives its tasks, and the queue it listens to.
INDEX_TASK = "template_matching.index_template"
REMOVE_TASK = "template_matching.remove_template"
QUEUE = "template_matching"


class TemplateIndexer(Protocol):
    def index(self, message: dict) -> None: ...

    def remove(self, template_id: str) -> None: ...


class CeleryIndexer:
    def __init__(self, broker_url: str) -> None:
        self._app = Celery("croquembouche_backend", broker=broker_url)
        # Do not hang a request on a broker that is down: a few quick tries, then give up.
        self._app.conf.update(
            broker_connection_timeout=2,
            broker_connection_retry=False,
            broker_transport_options={"socket_timeout": 2, "socket_connect_timeout": 2},
            task_publish_retry_policy={
                "max_retries": 1,
                "interval_start": 0,
                "interval_step": 0.2,
                "interval_max": 0.5,
            },
        )

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
