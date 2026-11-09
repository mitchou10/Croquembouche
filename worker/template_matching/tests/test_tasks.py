from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from app import config, tasks
from app.consumption import Measure


def test_ping():
    assert tasks.ping() == "pong"


@pytest.fixture
def fake_index(monkeypatch):
    index = MagicMock()
    index.index.return_value = {"pages": 2, "entities": 1}
    monkeypatch.setattr(tasks, "get_index", lambda: index)
    return index


def test_the_index_task_indexes_the_model_it_is_given(fake_index):
    template = {"template_id": "t1", "document_id": "d", "pages": [], "entities": []}

    assert tasks.index_template(template) == {"pages": 2, "entities": 1}
    fake_index.index.assert_called_once_with(template)


def test_the_remove_task_removes_a_model(fake_index):
    tasks.remove_template("t1")

    fake_index.remove.assert_called_once_with("t1")


def test_the_tasks_try_again_when_something_is_not_ready():
    for task in (tasks.index_template, tasks.remove_template, tasks.classify_pages, tasks.find_neighbours):
        assert task.autoretry_for == (Exception,) and task.retry_backoff and task.retry_kwargs["max_retries"] == 4


def test_the_index_is_built_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(tasks, "_index", None)
    built = []
    monkeypatch.setattr(tasks, "QdrantClient", lambda url: built.append(url) or MagicMock())
    monkeypatch.setattr(tasks.embeddings, "get_embedder", lambda: MagicMock(dimension=4, name="m"))

    first = tasks.get_index()

    assert tasks.get_index() is first and built == [config.QDRANT_URL]
    monkeypatch.setattr(tasks, "_index", None)


def test_each_model_has_a_collection_of_its_own(monkeypatch):
    monkeypatch.setattr(config, "QDRANT_COLLECTION", "templates")
    monkeypatch.setattr(config, "EMBEDDING_MODEL", "Qdrant/clip-ViT-B-32-vision")
    clip = config.collection_name()
    monkeypatch.setattr(config, "EMBEDDING_MODEL", "google/siglip2-base-patch16-224")

    assert clip == "templates--qdrant-clip-vit-b-32-vision"
    assert config.collection_name() == "templates--google-siglip2-base-patch16-224"


def test_the_classify_task_reads_the_pages_and_classifies_them(monkeypatch):
    classifier = MagicMock()
    classifier.classify.return_value = [{"page": 1, "classifications": []}]
    monkeypatch.setattr(tasks, "get_classifier", lambda: classifier)
    monkeypatch.setattr(tasks.storage, "get_bytes", lambda key: key.encode())

    assert tasks.classify_pages(["t1"], ["a", "b"]) == [{"page": 1, "classifications": []}]
    classifier.classify.assert_called_once_with(["t1"], [b"a", b"b"])


def test_the_classifier_is_built_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(tasks, "_classifier", None)
    monkeypatch.setattr(tasks, "QdrantClient", lambda url: MagicMock())
    monkeypatch.setattr(tasks.embeddings, "get_embedder", lambda: MagicMock())

    first = tasks.get_classifier()

    assert tasks.get_classifier() is first
    monkeypatch.setattr(tasks, "_classifier", None)


def test_what_a_use_consumed_goes_with_its_answer(monkeypatch):
    reported = []
    monkeypatch.setattr(tasks, "get_classifier", lambda: MagicMock())
    monkeypatch.setattr(tasks, "match", lambda *args: {"status": "done", "pages": [], "found": []})
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: reported.append((run_id, result)))
    used = {"energy_kwh": 0.001, "co2_kg": 0.00005, "duration_s": 2.5}

    @contextmanager
    def measured(name):
        measure = Measure()
        measure.value = used
        yield measure

    monkeypatch.setattr(tasks, "measured", measured)

    tasks.match_document({"run_id": "r1"})

    assert reported == [("r1", {"status": "done", "pages": [], "found": [], "consumption": used})]


def test_a_search_reads_the_pages_looks_for_the_neighbours_and_hands_back_what_it_consumed(monkeypatch):
    reported = []
    searcher = MagicMock()
    searcher.search.return_value = {"status": "done", "neighbours": [], "links": []}
    monkeypatch.setattr(tasks, "get_searcher", lambda: searcher)
    monkeypatch.setattr(tasks.storage, "get_bytes", lambda key: key.encode())
    monkeypatch.setattr(tasks.backend, "report_search", lambda search_id, result: reported.append((search_id, result)))
    used = {"energy_kwh": 0.001, "co2_kg": 0.00005, "duration_s": 2.5}

    @contextmanager
    def measured(name):
        measure = Measure()
        measure.value = used
        yield measure

    monkeypatch.setattr(tasks, "measured", measured)

    tasks.find_neighbours({"search_id": "s1", "page_keys": ["a", "b"], "k": 4, "template_ids": ["t1"]})

    searcher.search.assert_called_once_with([b"a", b"b"], 4, ["t1"])
    assert reported == [("s1", {"status": "done", "neighbours": [], "links": [], "consumption": used})]


def test_a_search_with_no_model_asked_looks_in_every_one(monkeypatch):
    searcher = MagicMock()
    searcher.search.return_value = {"status": "done", "neighbours": [], "links": []}
    monkeypatch.setattr(tasks, "get_searcher", lambda: searcher)
    monkeypatch.setattr(tasks.storage, "get_bytes", lambda key: key.encode())
    monkeypatch.setattr(tasks.backend, "report_search", lambda *args: None)

    tasks.find_neighbours({"search_id": "s1", "page_keys": ["a"], "k": 6, "template_ids": None})

    searcher.search.assert_called_once_with([b"a"], 6, None)


def test_a_search_that_cannot_be_made_ends_as_failed_on_the_backend(monkeypatch):
    reported = []
    monkeypatch.setattr(tasks.backend, "report_search", lambda search_id, result: reported.append((search_id, result)))

    tasks._ReportsSearchFailure().on_failure(RuntimeError("boom"), "id", [{"search_id": "s1"}], {}, None)

    assert reported == [("s1", {"status": "failed"})]


def test_a_search_that_cannot_even_be_reported_as_failed_is_only_logged(monkeypatch):
    def down(*args):
        raise ConnectionError("backend down")

    monkeypatch.setattr(tasks.backend, "report_search", down)

    tasks._ReportsSearchFailure().on_failure(RuntimeError("boom"), "id", [{"search_id": "s1"}], {}, None)


def test_the_searcher_is_built_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(tasks, "_searcher", None)
    monkeypatch.setattr(tasks, "QdrantClient", lambda url: MagicMock())
    monkeypatch.setattr(tasks.embeddings, "get_embedder", lambda: MagicMock())

    first = tasks.get_searcher()

    assert tasks.get_searcher() is first
    monkeypatch.setattr(tasks, "_searcher", None)
