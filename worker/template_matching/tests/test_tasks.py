from unittest.mock import MagicMock

import pytest

from app import config, tasks


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
    for task in (tasks.index_template, tasks.remove_template):
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
