from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core import storage


def _error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "op")


@pytest.fixture
def client(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(storage, "_client", fake)
    monkeypatch.setattr(storage, "_bucket_ready", False)
    return fake


def test_the_bucket_is_created_once_when_it_is_missing(client):
    client.head_bucket.side_effect = _error("404")

    storage.put_object("k", b"data", "text/plain")
    storage.put_object("k2", b"data")

    client.create_bucket.assert_called_once()
    assert client.put_object.call_args_list[0].kwargs["ContentType"] == "text/plain"


def test_an_existing_bucket_is_left_alone(client):
    storage.put_object("k", b"data")

    client.create_bucket.assert_not_called()


def test_an_object_is_read_back_with_its_type(client):
    client.get_object.return_value = {"Body": MagicMock(read=lambda: b"data"), "ContentType": "image/png"}

    assert storage.get_object("k") == (b"data", "image/png")


def test_a_missing_object_is_said_so(client):
    client.get_object.side_effect = _error("NoSuchKey")

    with pytest.raises(storage.ObjectNotFoundError):
        storage.get_object("k")


def test_any_other_failure_is_not_hidden(client):
    client.get_object.side_effect = _error("AccessDenied")

    with pytest.raises(ClientError):
        storage.get_object("k")


def test_a_prefix_is_deleted_page_by_page(client):
    client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "p/a"}, {"Key": "p/b"}]},
        {},
    ]

    storage.delete_prefix("p/")

    client.delete_objects.assert_called_once()
    assert client.delete_objects.call_args.kwargs["Delete"] == {"Objects": [{"Key": "p/a"}, {"Key": "p/b"}]}
