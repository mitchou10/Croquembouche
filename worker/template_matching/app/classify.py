"""What each page of an analysed document is: the page of a model of the catalogue it looks most like, with how much
it looks like it, « other » being one of the answers.

A page is embedded and its nearest neighbours are looked up among the pages of the models of the analysis. A model
page is indexed turned four ways, and in every X of the model (each X is another example document), so a neighbour is a
(model, X, page, rotation): the best score of each (model, page) is kept, whatever the X and the rotation, and the X and
the rotation that gave it are said.

The score of a page is its similarity, as it is (the cosine, from 0 to 1), not shared among the answers: the page is the
one it looks the most like, as long as that is at least the threshold, and « other » when nothing reaches it."""

import io
from typing import Any

from PIL import Image
from qdrant_client import QdrantClient, models

from app import config


class PageClassifier:
    def __init__(
        self,
        client: QdrantClient,
        embedder: Any,
        collection: str,
        threshold: float = config.MATCH_THRESHOLD,
        neighbours: int = config.NEIGHBOURS,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._threshold = threshold
        self._neighbours = neighbours

    def classify(self, template_ids: list[str], pages: list[bytes], pinned: dict[str, int] | None = None) -> list[dict]:
        """For each page of the document (from 1), what it could be, the likeliest first:
        `{page, classifications: [{template_id, template_page, confidence, rotation, major}]}`: `confidence` is the
        similarity (0 to 1), `major` the X of the model that the page looks like, `template_page` a page of it.
        « other » has no model, no page, no X and no rotation, and the threshold as its score: it comes first when no
        page reaches the threshold. With no model to compare to, every page is « other ». `pinned`: models that are only
        looked for in one X (`{template_id: X}`), as an analysis pinned to a version asks."""
        images = [Image.open(io.BytesIO(data)).convert("RGB") for data in pages]
        vectors = self._embedder.embed(images) if images and template_ids else [[] for _ in images]
        return [
            {"page": number, "classifications": self._classes(template_ids, vector, pinned or {})}
            for number, vector in enumerate(vectors, start=1)
        ]

    @staticmethod
    def _models_filter(template_ids: list[str], pinned: dict[str, int]) -> models.Filter:
        """The models looked for: any X of those that are not pinned, the X asked for of those that are (a page indexed
        before the X was kept is the first)."""
        free = [t for t in template_ids if t not in pinned]
        should: list[models.Condition] = (
            [models.FieldCondition(key="template_id", match=models.MatchAny(any=free))] if free else []
        )
        for template_id, major in pinned.items():
            in_that_x: list[models.Condition] = [
                models.FieldCondition(key="major", match=models.MatchValue(value=major))
            ]
            if major == 1:
                in_that_x.append(models.IsEmptyCondition(is_empty=models.PayloadField(key="major")))
            should.append(
                models.Filter(
                    must=[
                        models.FieldCondition(key="template_id", match=models.MatchValue(value=template_id)),
                        models.Filter(should=in_that_x),
                    ]
                )
            )
        return models.Filter(should=should)

    def _classes(self, template_ids: list[str], vector: list[float], pinned: dict[str, int]) -> list[dict]:
        best: dict[tuple[str, int], tuple[float, int, int]] = {}
        if template_ids:
            found = self._client.query_points(
                self._collection,
                query=vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="kind", match=models.MatchValue(value="page")),
                        self._models_filter(template_ids, pinned),
                    ]
                ),
                limit=self._neighbours,
                with_payload=True,
            ).points
            for point in found:
                key = (point.payload["template_id"], point.payload["page"])
                if key not in best or point.score > best[key][0]:
                    # An entry indexed before the X was kept is the first X.
                    best[key] = (point.score, point.payload["rotation"], point.payload.get("major", 1))
        classes = [
            {
                "template_id": t,
                "template_page": p,
                "confidence": min(1.0, max(0.0, score)),
                "rotation": rotation,
                "major": major,
            }
            for (t, p), (score, rotation, major) in best.items()
        ]
        classes.append(
            {
                "template_id": None,
                "template_page": None,
                # Nothing to compare to: « other » is the only answer, and a sure one.
                "confidence": self._threshold if template_ids else 1.0,
                "rotation": None,
                "major": None,
            }
        )
        # A page that is exactly at the threshold is that page: the sort is stable and « other » comes last.
        return sorted(classes, key=lambda c: -c["confidence"])
