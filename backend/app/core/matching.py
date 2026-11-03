"""Asking the worker to match a document: it does all the computing, the backend only says what to look at and keeps
what comes back (see `routers/internal.py`)."""

from typing import Protocol

from app.config import RedisSettings
from app.core.worker import QUEUE, make_client

MATCH_TASK = "template_matching.match_document"


class MatchingDispatcher(Protocol):
    def dispatch(self, message: dict) -> None:
        """Raises when the worker cannot be asked: the use is then ended as failed instead of waiting for nothing."""
        ...


class CeleryDispatcher:
    def __init__(self, broker_url: str) -> None:
        self._app = make_client(broker_url)

    def dispatch(self, message: dict) -> None:
        self._app.send_task(MATCH_TASK, args=[message], queue=QUEUE)


_dispatcher: MatchingDispatcher | None = None


def get_dispatcher() -> MatchingDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CeleryDispatcher(RedisSettings().REDIS_URL)
    return _dispatcher
