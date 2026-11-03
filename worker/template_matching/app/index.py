"""The catalogue as the matching sees it: one vector for each page of the example document of a model, and one for
each entity drawn on it (the crop of its zone). The backend says what a model is made of; this keeps the vector store
in step.

A point has a fixed identifier made from what it is (a page, an entity of a model), so indexing a model again replaces
its points instead of adding to them, and what the model no longer has (a page, an entity) is removed."""

import io
import uuid
from collections.abc import Callable
from typing import Any

from PIL import Image
from qdrant_client import QdrantClient, models

# Around a zone, so that its edge is seen with a little of what is around it; and no smaller than a model can read.
CROP_MARGIN = 0.02
MIN_CROP_SIDE = 32
BATCH = 32

_NAMESPACE = uuid.UUID("6b1f0c5e-3d1e-4c70-9a43-0f5c9f2a7e10")


def point_id(kind: str, template_id: str, ref: str | int) -> str:
    """The same page or entity of the same model always has the same identifier."""
    return str(uuid.uuid5(_NAMESPACE, f"{kind}:{template_id}:{ref}"))


def crop_zone(image: Image.Image, points: list[dict[str, float]]) -> Image.Image | None:
    """The part of a page a zone covers (the zone is in fractions of the page), with a margin; None when the zone is
    empty or off the page."""
    if len(points) < 3:
        return None
    width, height = image.size
    xs, ys = [p["x"] for p in points], [p["y"] for p in points]
    left = max(0.0, min(xs) - CROP_MARGIN) * width
    top = max(0.0, min(ys) - CROP_MARGIN) * height
    right = min(1.0, max(xs) + CROP_MARGIN) * width
    bottom = min(1.0, max(ys) + CROP_MARGIN) * height
    if right <= left or bottom <= top:
        return None
    # A zone smaller than the least a model can read is widened around its centre.
    if right - left < MIN_CROP_SIDE:
        middle = (left + right) / 2
        left, right = max(0.0, middle - MIN_CROP_SIDE / 2), min(float(width), middle + MIN_CROP_SIDE / 2)
    if bottom - top < MIN_CROP_SIDE:
        middle = (top + bottom) / 2
        top, bottom = max(0.0, middle - MIN_CROP_SIDE / 2), min(float(height), middle + MIN_CROP_SIDE / 2)
    return image.crop((round(left), round(top), round(right), round(bottom)))


def _batches(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


class TemplateIndex:
    def __init__(
        self,
        client: QdrantClient,
        embedder: Any,
        read: Callable[[str], bytes],
        collection: str,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._read = read
        self._collection = collection
        self._ready = False

    def ensure_collection(self) -> None:
        if self._ready:
            return
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(size=self._embedder.dimension, distance=models.Distance.COSINE),
            )
        # What a search is restricted to, and what is removed with a model.
        self._client.create_payload_index(self._collection, "template_id", models.PayloadSchemaType.KEYWORD)
        self._ready = True

    def index(self, template: dict) -> dict[str, int]:
        """Brings the index of a model up to date with what it is now: `template` is `{template_id, document_id,
        pages: [{page, key, name, description}], entities: [{id, name, page, points}]}`. Returns how many points there
        are for it."""
        self.ensure_collection()
        template_id = template["template_id"]
        images: dict[int, Image.Image] = {}
        for page in template["pages"]:
            images[page["page"]] = Image.open(io.BytesIO(self._read(page["key"]))).convert("RGB")

        wanted: list[tuple[str, Image.Image, dict]] = []
        for page in template["pages"]:
            payload = {
                "kind": "page",
                "page": page["page"],
                "name": page.get("name") or "",
                "description": page.get("description") or "",
            }
            wanted.append((point_id("page", template_id, page["page"]), images[page["page"]], payload))
        for entity in template.get("entities", []):
            image = images.get(entity.get("page"))
            crop = crop_zone(image, entity["points"]) if image is not None else None
            if crop is not None:
                payload = {
                    "kind": "entity",
                    "page": entity["page"],
                    "entity_id": entity["id"],
                    "name": entity.get("name") or "",
                }
                wanted.append((point_id("entity", template_id, entity["id"]), crop, payload))

        for batch in _batches(wanted, BATCH):
            vectors = self._embedder.embed([image for _, image, _ in batch])
            self._client.upsert(
                self._collection,
                points=[
                    models.PointStruct(
                        id=identifier,
                        vector=vector,
                        payload={
                            **payload,
                            "template_id": template_id,
                            "document_id": template["document_id"],
                            "model": self._embedder.name,
                        },
                    )
                    for (identifier, _, payload), vector in zip(batch, vectors, strict=True)
                ],
            )
        # What the model no longer has (a page taken away with its document, an entity deleted) leaves the index.
        self._client.delete(
            self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="template_id", match=models.MatchValue(value=template_id))],
                    must_not=[models.HasIdCondition(has_id=[identifier for identifier, _, _ in wanted])],
                )
            ),
        )
        return {
            "pages": sum(1 for _, _, p in wanted if p["kind"] == "page"),
            "entities": sum(1 for _, _, p in wanted if p["kind"] == "entity"),
        }

    def remove(self, template_id: str) -> None:
        """Takes a model out of the index: everything it had."""
        self.ensure_collection()
        self._client.delete(
            self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="template_id", match=models.MatchValue(value=template_id))]
                )
            ),
        )
