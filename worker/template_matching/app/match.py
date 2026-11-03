"""What a document is, page by page, and where the elements of its models are on it: the classification of each page
(see `classify`), then, for the model page it was classified as, the zones carried over onto it (see `project`)."""

import logging
from collections.abc import Callable

from app.classify import PageClassifier
from app.project import locate

logger = logging.getLogger(__name__)


def _zones(template: dict, page: int) -> list[dict]:
    """The entities of a model that have a zone on this page of it."""
    return [e for e in template.get("entities", []) if e.get("page") == page and e.get("points")]


def _found(page: int, template_id: str, confidence: float, entity_id: str, points: list[dict]) -> dict:
    return {
        "page": page,
        "entity_id": entity_id,
        "points": points,
        # An element is as sure as the page is of being that model page, and as the keypoints are of agreeing.
        "classifications": [
            {"template_id": template_id, "confidence": confidence},
            {"template_id": None, "confidence": round(1 - confidence, 6)},
        ],
    }


def match_document(
    classifier: PageClassifier,
    read: Callable[[str], bytes],
    message: dict,
) -> dict:
    """`message` is `{run_id, templates: [{template_id, pages: [{page, key}], entities: [{id, page, points}]}],
    page_keys}`. Returns `{status, pages, found}`: what each page could be, and the elements found in them. A page whose
    zones cannot be carried over is classified all the same: it loses its elements, not the other pages."""
    templates = {t["template_id"]: t for t in message["templates"] if t.get("pages")}
    pages = [read(key) for key in message["page_keys"]]
    classified = classifier.classify(list(templates), pages)

    found: list[dict] = []
    for result in classified:
        top = result["classifications"][0]
        if top["template_id"] is None:
            continue
        template = templates[top["template_id"]]
        entities = _zones(template, top["template_page"])
        if not entities:
            continue
        number = result["page"]
        try:
            key = next(p["key"] for p in template["pages"] if p["page"] == top["template_page"])
            instances = locate(read(key), pages[number - 1], [e["points"] for e in entities])
        except Exception:
            logger.exception("Could not carry the zones of %s onto page %s", top["template_id"], number)
            continue
        for instance in instances:
            confidence = round(top["confidence"] * instance.confidence, 6)
            for entity, points in zip(entities, instance.zones, strict=True):
                found.append(_found(number, top["template_id"], confidence, entity["id"], points))

    return {
        "status": "done",
        "pages": [
            {
                "page": r["page"],
                "classifications": [
                    {
                        "template_id": c["template_id"],
                        "template_page": c["template_page"],
                        "confidence": c["confidence"],
                    }
                    for c in r["classifications"]
                ],
            }
            for r in classified
        ],
        "found": found,
    }
