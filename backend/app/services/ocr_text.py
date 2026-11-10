"""The text of a zone: the lines the OCR read that lie in it.

Only an entity that is read has one. An image (a signature, a logo) has no text to read, and a table will be
read another way: neither is given the lines that happen to fall in its zone."""

import uuid

from app.models.catalogue import Template, TemplateVersion
from app.schemas.matching import OcrLine, OcrPage

# The types of entity whose zone is not read as text.
NOT_TEXT = frozenset({"image", "table"})


def is_read(entity_type: str | None) -> bool:
    """Whether the text of the zone is the value of the entity (or, for an element with no known entity, a hint)."""
    return entity_type not in NOT_TEXT


def _inside(x: float, y: float, polygon: list[dict[str, float]]) -> bool:
    """Ray casting: whether a point is in a polygon."""
    inside = False
    for a, b in zip(polygon, [*polygon[1:], polygon[0]], strict=True):
        if (a["y"] > y) != (b["y"] > y) and x < (b["x"] - a["x"]) * (y - a["y"]) / (b["y"] - a["y"]) + a["x"]:
            inside = not inside
    return inside


def _centre(line: OcrLine) -> tuple[float, float]:
    return (sum(p.x for p in line.points) / len(line.points), sum(p.y for p in line.points) / len(line.points))


def text_in_zone(pages: list[OcrPage], page: int, polygon: list[dict[str, float]]) -> str:
    """The lines of the page whose centre is in the zone, top to bottom then left to right, one per line. Empty when the
    zone has nothing in it."""
    if len(polygon) < 3:
        return ""
    found = []
    for ocr_page in pages:
        if ocr_page.page != page:
            continue
        for line in ocr_page.lines:
            if line.points and _inside(*_centre(line), polygon):
                found.append((line, _centre(line)))
    # Lines of one row are at about the same height: a row is a tenth of the page.
    found.sort(key=lambda item: (round(item[1][1] * 40), item[1][0]))
    return "\n".join(line.text for line, _ in found)


def _entities_of(template: Template, version: TemplateVersion | None) -> tuple[bool, list[tuple]]:
    """Whether the model has no document, and its entities as `(id, name, definition, type, examples, has_zone)`: as
    it is now, or as it was in the version an analysis is pinned to."""
    if version is None:
        return template.document is None, [
            (e.id, e.name, e.definition, e.type, e.examples, any(z.points for z in e.zones)) for e in template.entities
        ]
    return version.document is None, [
        (
            e["id"],
            e["name"],
            e["definition"],
            e["type"],
            e["examples"],
            any(z["points"] for z in e.get("zones") or [e.get("zone")] if z),
        )
        for e in version.snapshot["entities"]
    ]


def entities_to_find(templates: list[Template], pinned: dict[uuid.UUID, TemplateVersion] | None = None) -> list[dict]:
    """The entities the OCR worker finds in the text, by their definition: the ones with no zone to be carried over
    onto the document, so those of a model with no document (it has no zone at all) and the others of a model that has
    one. An image or a table has no text to find. `pinned`: the version some models are looked for as."""
    found = []
    for template in templates:
        no_document, entities = _entities_of(template, (pinned or {}).get(template.id))
        found.extend(
            {
                "id": str(identifier),
                "template_id": str(template.id),
                "name": name,
                "definition": definition,
                "type": type_,
                "examples": examples,
            }
            for identifier, name, definition, type_, examples, has_zone in entities
            if is_read(type_) and (no_document or not has_zone)
        )
    return found
