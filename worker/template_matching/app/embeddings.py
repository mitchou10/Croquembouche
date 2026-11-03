from typing import Protocol

from PIL import Image

from app import config


class Embedder(Protocol):
    """Turns images into vectors that are close when the images look alike."""

    name: str
    dimension: int

    def embed(self, images: list[Image.Image]) -> list[list[float]]: ...


class FastEmbedder:
    """An image embedding model of fastembed (CLIP, SigLIP...: ONNX, no torch). The weights are downloaded on first use,
    into the cache directory, and the model is loaded on the first image."""

    def __init__(self, name: str, cache_dir: str | None = None) -> None:
        from fastembed import ImageEmbedding

        self.name = name
        self._cache_dir = cache_dir
        self._model: ImageEmbedding | None = None
        supported = {m["model"]: m for m in ImageEmbedding.list_supported_models()}
        if name not in supported:
            raise ValueError(f"Unknown image embedding model {name!r}; known: {', '.join(sorted(supported))}")
        self.dimension = int(supported[name]["dim"])

    def embed(self, images: list[Image.Image]) -> list[list[float]]:
        if self._model is None:
            from fastembed import ImageEmbedding

            self._model = ImageEmbedding(self.name, cache_dir=self._cache_dir)
        return [vector.tolist() for vector in self._model.embed(images)]


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = FastEmbedder(config.EMBEDDING_MODEL, config.EMBEDDING_CACHE_DIR)
    return _embedder
