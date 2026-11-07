"""Asking the worker to match a document: it does all the computing, the backend only says what to look at and keeps
what comes back (see `routers/internal.py`)."""

from typing import Protocol

from app.config import RedisSettings
from app.core.worker import QUEUE, make_client

MATCH_TASK = "template_matching.match_document"
OCR_TASK = "ocr.read_document"
OCR_QUEUE = "ocr"
FIND_TASK = "gliner.find_entities"
FIND_QUEUE = "gliner"


class MatchingDispatcher(Protocol):
    def dispatch(self, message: dict) -> None:
        """Raises when the worker cannot be asked: the use is then ended as failed instead of waiting for nothing."""
        ...

    def dispatch_ocr(self, message: dict) -> None:
        """Asks the OCR worker to read the text of the document, beside the matching: nothing waits for it. Raises when
        it cannot be asked, which only costs the text."""
        ...

    def dispatch_find(self, message: dict) -> None:
        """Asks the GLiNER worker to find the entities that have no zone in the text the OCR read. Raises when it cannot
        be asked, which only costs those elements."""
        ...

    def revoke(self, run_id: str) -> None:
        """Asks the workers to stop the matching, the reading and the search of a run, if they have not ended. Only an
        attempt: what they would hand back for a cancelled run is ignored anyway."""
        ...


def ocr_task_id(run_id: str) -> str:
    return f"ocr-{run_id}"


def find_task_id(run_id: str) -> str:
    return f"gliner-{run_id}"


class CeleryDispatcher:
    def __init__(self, broker_url: str) -> None:
        self._app = make_client(broker_url)

    def dispatch(self, message: dict) -> None:
        # The task is the run's: that is what is revoked to cancel it.
        self._app.send_task(MATCH_TASK, args=[message], queue=QUEUE, task_id=message["run_id"])

    def dispatch_ocr(self, message: dict) -> None:
        self._app.send_task(OCR_TASK, args=[message], queue=OCR_QUEUE, task_id=ocr_task_id(message["run_id"]))

    def dispatch_find(self, message: dict) -> None:
        self._app.send_task(FIND_TASK, args=[message], queue=FIND_QUEUE, task_id=find_task_id(message["run_id"]))

    def revoke(self, run_id: str) -> None:
        self._app.control.revoke([run_id, ocr_task_id(run_id), find_task_id(run_id)], terminate=True)


_dispatcher: MatchingDispatcher | None = None


def get_dispatcher() -> MatchingDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CeleryDispatcher(RedisSettings().REDIS_URL)
    return _dispatcher
