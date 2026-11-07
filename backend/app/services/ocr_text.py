"""The text of a zone: the lines the OCR read that lie in it.

Only an entity that is read has one. An image (a signature, a logo) has no text to read, and a table will be
read another way: neither is given the lines that happen to fall in its zone."""

from app.models.catalogue import Template
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


def entities_to_find(templates: list[Template]) -> list[dict]:
    """The entities the OCR worker finds in the text, by their definition: the ones with no zone to be carried over
    onto the document, so those of a model with no document (it has no zone at all) and the others of a model that has
    one. An image or a table has no text to find."""
    return [
        {
            "id": str(e.id),
            "template_id": str(template.id),
            "name": e.name,
            "definition": e.definition,
            "type": e.type,
            "examples": e.examples,
        }
        for template in templates
        for e in template.entities
        if is_read(e.type) and (template.document is None or e.zone_page is None or not e.zone_points)
    ]
