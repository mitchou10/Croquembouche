from unittest.mock import MagicMock

import pytest

from app.core import matching
from app.core.matching import MATCH_TASK, OCR_QUEUE, OCR_TASK, CeleryDispatcher
from app.core.worker import QUEUE


def test_the_worker_is_asked_to_match_by_name_on_its_queue(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    send = MagicMock()
    monkeypatch.setattr(dispatcher._app, "send_task", send)

    dispatcher.dispatch({"run_id": "r1"})

    assert send.call_args.args == (MATCH_TASK,)
    # The task is the run's, which is what is revoked to cancel it.
    assert send.call_args.kwargs == {"args": [{"run_id": "r1"}], "queue": QUEUE, "task_id": "r1"}


def test_the_ocr_worker_is_asked_to_read_on_its_own_queue(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    send = MagicMock()
    monkeypatch.setattr(dispatcher._app, "send_task", send)

    dispatcher.dispatch_ocr({"run_id": "r1"})

    assert send.call_args.args == (OCR_TASK,)
    assert send.call_args.kwargs == {"args": [{"run_id": "r1"}], "queue": OCR_QUEUE, "task_id": "ocr-r1"}


def test_the_gliner_worker_is_asked_to_find_on_its_own_queue(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    send = MagicMock()
    monkeypatch.setattr(dispatcher._app, "send_task", send)

    dispatcher.dispatch_find({"run_id": "r1"})

    assert send.call_args.args == ("gliner.find_entities",)
    assert send.call_args.kwargs == {"args": [{"run_id": "r1"}], "queue": "gliner", "task_id": "gliner-r1"}


def test_the_task_of_a_run_is_revoked_to_cancel_it(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    revoke = MagicMock()
    monkeypatch.setattr(dispatcher._app.control, "revoke", revoke)

    dispatcher.revoke("r1")

    revoke.assert_called_once_with(["r1", "ocr-r1", "gliner-r1"], terminate=True)


def test_a_broker_that_is_down_is_not_hidden(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    monkeypatch.setattr(dispatcher._app, "send_task", MagicMock(side_effect=ConnectionError("down")))

    with pytest.raises(ConnectionError):
        dispatcher.dispatch({"run_id": "r1"})


def test_the_dispatcher_is_made_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(matching, "_dispatcher", None)

    first = matching.get_dispatcher()

    assert matching.get_dispatcher() is first and isinstance(first, CeleryDispatcher)
    monkeypatch.setattr(matching, "_dispatcher", None)
