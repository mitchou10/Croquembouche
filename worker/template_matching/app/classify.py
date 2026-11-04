"""What each page of an analysed document is: the page of a model of the catalogue it looks most like, with how sure
that is, « other » being one of the answers.

A page is embedded and its nearest neighbours are looked up among the pages of the models of the analysis. A model
page is indexed turned four ways, and in every X of the model (each X is another example document), so a neighbour is a
(model, X, page, rotation): the best score of each (model, page) is kept, whatever the X and the rotation, and the X and
the rotation that gave it are said."""

import io
import math
from typing import Any

from PIL import Image
from qdrant_client import QdrantClient, models

from app import config


def calibrate(scores: list[float], other_score: float, temperature: float) -> tuple[list[float], float]:
    """Similarities to confidences that add up to 1, with « other » as one more class: a softmax of the scores over
    `temperature`, where « other » stands for a page that scores `other_score`. A page that looks like nothing in the
    catalogue gets most of it to « other »; one that looks like a single page gets most of it to that page."""
    logits = [score / temperature for score in scores] + [other_score / temperature]
    top = max(logits)
    weights = [math.exp(logit - top) for logit in logits]
    total = sum(weights)
    return [w / total for w in weights[:-1]], weights[-1] / total


class PageClassifier:
    def __init__(
        self,
        client: QdrantClient,
        embedder: Any,
        collection: str,
        other_score: float = config.OTHER_SCORE,
        temperature: float = config.TEMPERATURE,
        neighbours: int = config.NEIGHBOURS,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._other_score = other_score
        self._temperature = temperature
        self._neighbours = neighbours

    def classify(self, template_ids: list[str], pages: list[bytes]) -> list[dict]:
        """For each page of the document (from 1), what it could be, the likeliest first:
        `{page, classifications: [{template_id, template_page, confidence, rotation, major}]}`: `major` is the X of the
        model that the page looks like, `template_page` a page of it. « other » has no model, no page, no X and no
        rotation. With no model to compare to, every page is « other »."""
        images = [Image.open(io.BytesIO(data)).convert("RGB") for data in pages]
        vectors = self._embedder.embed(images) if images and template_ids else [[] for _ in images]
        return [
            {"page": number, "classifications": self._classes(template_ids, vector)}
            for number, vector in enumerate(vectors, start=1)
        ]

    def _classes(self, template_ids: list[str], vector: list[float]) -> list[dict]:
        best: dict[tuple[str, int], tuple[float, int, int]] = {}
        if template_ids:
            found = self._client.query_points(
                self._collection,
                query=vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="kind", match=models.MatchValue(value="page")),
                        models.FieldCondition(key="template_id", match=models.MatchAny(any=template_ids)),
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
        keys = list(best)
        confidences, other = calibrate([best[k][0] for k in keys], self._other_score, self._temperature)
        classes = [
            {
                "template_id": t,
                "template_page": p,
                "confidence": c,
                "rotation": best[(t, p)][1],
                "major": best[(t, p)][2],
            }
            for (t, p), c in zip(keys, confidences, strict=True)
        ]
        classes.append(
            {"template_id": None, "template_page": None, "confidence": other, "rotation": None, "major": None}
        )
        return sorted(classes, key=lambda c: -c["confidence"])
