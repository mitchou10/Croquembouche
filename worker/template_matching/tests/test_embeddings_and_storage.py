from unittest.mock import MagicMock

import pytest
from PIL import Image

from app import config, embeddings, storage


def test_a_model_fastembed_does_not_know_is_refused_with_the_known_ones():
    with pytest.raises(ValueError, match="Qdrant/clip-ViT-B-32-vision"):
        embeddings.FastEmbedder("nope/not-a-model")


def test_the_size_of_the_vectors_is_the_one_of_the_model():
    assert embeddings.FastEmbedder("Qdrant/clip-ViT-B-32-vision").dimension == 512


def test_the_model_is_loaded_on_the_first_images_and_only_then(monkeypatch):
    import fastembed

    loaded = []

    class FakeModel:
        def __init__(self, name, cache_dir=None):
            loaded.append((name, cache_dir))

        def embed(self, images):
            return [MagicMock(tolist=lambda: [0.5, 0.5]) for _ in images]

    monkeypatch.setattr(
        fastembed,
        "ImageEmbedding",
        type(
            "E", (FakeModel,), {"list_supported_models": staticmethod(fastembed.ImageEmbedding.list_supported_models)}
        ),
    )
    embedder = embeddings.FastEmbedder("Qdrant/clip-ViT-B-32-vision", "/cache")
    assert loaded == []

    assert embedder.embed([Image.new("RGB", (4, 4))]) == [[0.5, 0.5]]
    embedder.embed([Image.new("RGB", (4, 4))])
    assert loaded == [("Qdrant/clip-ViT-B-32-vision", "/cache")]


def test_the_embedder_is_made_once_from_the_settings(monkeypatch):
    monkeypatch.setattr(embeddings, "_embedder", None)
    monkeypatch.setattr(config, "EMBEDDING_MODEL", "Qdrant/clip-ViT-B-32-vision")

    first = embeddings.get_embedder()

    assert embeddings.get_embedder() is first and first.name == "Qdrant/clip-ViT-B-32-vision"
    monkeypatch.setattr(embeddings, "_embedder", None)


def test_a_page_is_read_from_the_bucket_with_a_client_made_on_first_use(monkeypatch):
    client = MagicMock()
    client.get_object.return_value = {"Body": MagicMock(read=lambda: b"png")}
    made = []
    monkeypatch.setattr(storage, "_client", None)
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: made.append(k) or client)

    assert storage.get_bytes("documents/d/pages/1.png") == b"png"
    storage.get_bytes("documents/d/pages/2.png")

    assert len(made) == 1 and made[0]["endpoint_url"] == config.AWS_ENDPOINT_URL
    client.get_object.assert_called_with(Bucket=config.AWS_BUCKET, Key="documents/d/pages/2.png")
    monkeypatch.setattr(storage, "_client", None)
