from unittest.mock import MagicMock

import pytest

from app.core import matching
from app.core.matching import MATCH_TASK, CeleryDispatcher
from app.core.worker import QUEUE


def test_the_worker_is_asked_to_match_by_name_on_its_queue(monkeypatch):
    dispatcher = CeleryDispatcher("redis://localhost:1/0")
    send = MagicMock()
    monkeypatch.setattr(dispatcher._app, "send_task", send)

    dispatcher.dispatch({"run_id": "r1"})

    assert send.call_args.args == (MATCH_TASK,)
    assert send.call_args.kwargs == {"args": [{"run_id": "r1"}], "queue": QUEUE}


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
