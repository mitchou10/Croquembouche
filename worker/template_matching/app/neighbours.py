"""The pages of the catalogue that look like the pages of a document that was sent: each page is embedded and its
nearest neighbours are looked up among the pages of the models (all of them, or the ones asked for).

A model page is indexed turned four ways, and in every X of the model (see `index`), so a neighbour is a (model, X,
page, rotation): the best score of each (model, page) is kept, whatever the X and the rotation, and the example
document of the X that gave it is said (to show the right image). The pages of the document are `page-N`, a neighbour
is `<model>:<page>`; a link between a page and a neighbour is how much they look like each other, and two neighbours
are linked when they look like each other too, which makes groups."""

import io
import math
from typing import Any

from PIL import Image
from qdrant_client import QdrantClient, models

from app import config


def page_node(page: int) -> str:
    return f"page-{page}"


def _unit(similarity: float) -> float:
    """A cosine as a similarity from 0 to 1: what looks nothing alike is 0, not negative."""
    return round(min(max(similarity, 0.0), 1.0), 4)


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0


class NeighbourSearch:
    def __init__(
        self,
        client: QdrantClient,
        embedder: Any,
        collection: str,
        link_min: float = config.SEARCH_LINK_MIN,
        points: int = config.NEIGHBOURS,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._link_min = link_min
        self._points = points

    def search(self, pages: list[bytes], k: int, template_ids: list[str] | None = None) -> dict:
        """`{status, neighbours: [{template_id, template_page, document_id, similarity}], links: [{source, target,
        similarity}]}`: for each page of the document (from 1), its `k` nearest pages of models, the likeliest first; a
        neighbour that is one of several pages' is one node, with the best of its similarities. With no model indexed
        (or none of the ones asked for), nothing is found."""
        if not pages or not self._client.collection_exists(self._collection):
            return {"status": "done", "neighbours": [], "links": []}
        images = [Image.open(io.BytesIO(data)).convert("RGB") for data in pages]
        vectors = self._embedder.embed(images)

        # Every neighbour with what it is, by node; every link of a page.
        nodes: dict[str, dict] = {}
        links: list[dict] = []
        for number, vector in enumerate(vectors, start=1):
            for node, found in self._nearest(vector, k, template_ids).items():
                if node not in nodes or found["similarity"] > nodes[node]["similarity"]:
                    nodes[node] = found
                links.append({"source": page_node(number), "target": node, "similarity": found["similarity"]})

        # The neighbours that look like each other: one link for a pair.
        ids = sorted(nodes)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                similarity = _cosine(nodes[a]["vector"], nodes[b]["vector"])
                if similarity >= self._link_min:
                    links.append({"source": a, "target": b, "similarity": _unit(similarity)})

        neighbours = [
            {
                "template_id": n["template_id"],
                "template_page": n["template_page"],
                "document_id": n["document_id"],
                "similarity": n["similarity"],
            }
            for n in sorted(nodes.values(), key=lambda n: (-n["similarity"], n["template_id"], n["template_page"]))
        ]
        return {"status": "done", "neighbours": neighbours, "links": links}

    def _nearest(self, vector: list[float], k: int, template_ids: list[str] | None) -> dict[str, dict]:
        """The `k` pages of models that look the most like a page, by node, each with its best similarity."""
        must = [models.FieldCondition(key="kind", match=models.MatchValue(value="page"))]
        if template_ids:
            must.append(models.FieldCondition(key="template_id", match=models.MatchAny(any=template_ids)))
        found = self._client.query_points(
            self._collection,
            query=vector,
            query_filter=models.Filter(must=must),
            limit=self._points,
            with_payload=True,
            with_vectors=True,
        ).points
        best: dict[str, dict] = {}
        for point in found:  # the likeliest first: the first of a page is its best, whatever the rotation or the X
            payload = point.payload
            node = f"{payload['template_id']}:{payload['page']}"
            if node not in best:
                best[node] = {
                    "template_id": payload["template_id"],
                    "template_page": payload["page"],
                    "document_id": payload["document_id"],
                    "similarity": _unit(point.score),
                    "vector": list(point.vector),
                }
        return dict(list(best.items())[:k])
