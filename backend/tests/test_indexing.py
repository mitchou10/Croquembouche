from unittest.mock import MagicMock

from app.core import indexing
from app.core.indexing import INDEX_TASK, QUEUE, REMOVE_TASK, CeleryIndexer


def test_the_worker_is_asked_by_name_on_its_queue(monkeypatch):
    indexer = CeleryIndexer("redis://localhost:1/0")
    send = MagicMock()
    monkeypatch.setattr(indexer._app, "send_task", send)

    indexer.index({"template_id": "t1"})
    indexer.remove("t1")

    assert send.call_args_list[0].args == (INDEX_TASK,) and send.call_args_list[0].kwargs == {
        "args": [{"template_id": "t1"}],
        "queue": QUEUE,
    }
    assert send.call_args_list[1].args == (REMOVE_TASK,) and send.call_args_list[1].kwargs["args"] == ["t1"]


def test_a_broker_that_is_down_does_not_break_what_asked(monkeypatch, caplog):
    indexer = CeleryIndexer("redis://localhost:1/0")
    monkeypatch.setattr(indexer._app, "send_task", MagicMock(side_effect=ConnectionError("down")))

    indexer.index({"template_id": "t1"})
    indexer.remove("t1")

    assert caplog.text.count("Could not ask the worker") == 2


def test_the_indexer_is_made_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(indexing, "_indexer", None)

    first = indexing.get_indexer()

    assert indexing.get_indexer() is first and isinstance(first, CeleryIndexer)
    monkeypatch.setattr(indexing, "_indexer", None)
