"""Finding an entity that has no zone: what its definition describes is looked for in the text the OCR read, with
GLiNER, and the place it was found at is given back as a zone (the corners of the lines it lies on).

An entity found this way has no model zone to carry over, so it is looked for on every page of the document and the
likeliest answer, over all of them, is kept."""

import logging

from app import config

logger = logging.getLogger(__name__)

_model = None


def get_model():
    """GLiNER, loaded on first use: a worker that only reads text never loads it (nor torch)."""
    global _model
    if _model is None:
        from gliner import GLiNER

        _model = GLiNER.from_pretrained(config.GLINER_MODEL)
    return _model


def label_of(entity: dict) -> str:
    """What GLiNER is asked to find: the definition of the entity, or its name when it has none."""
    return (entity.get("definition") or "").strip() or entity["name"].strip()


def _chunks(lines: list[dict]) -> list[list[dict]]:
    """The lines of a page in groups that GLiNER can read at once."""
    groups, current, words = [], [], 0
    for line in lines:
        count = len(line["text"].split())
        if current and words + count > config.GLINER_CHUNK_WORDS:
            groups.append(current)
            current, words = [], 0
        current.append(line)
        words += count
    return [*groups, current] if current else groups


def _lerp(a: dict, b: dict, t: float) -> dict:
    return {"x": a["x"] + (b["x"] - a["x"]) * t, "y": a["y"] + (b["y"] - a["y"]) * t}


def _part_of_line(line: dict, first: int, last: int) -> list[dict]:
    """The corners of the part of a line between two characters, along its top and its bottom edge (a line is given as
    its four corners, top-left first, whatever its orientation on the page)."""
    top_left, top_right, bottom_right, bottom_left = line["points"][:4]
    size = max(len(line["text"]), 1)
    a, b = first / size, last / size
    return [
        _lerp(top_left, top_right, a),
        _lerp(top_left, top_right, b),
        _lerp(bottom_left, bottom_right, b),
        _lerp(bottom_left, bottom_right, a),
    ]


def _zone(parts: list[list[dict]]) -> list[dict]:
    """One line: its part. Several: the rectangle around all of them."""
    if len(parts) == 1:
        return [{"x": round(p["x"], 4), "y": round(p["y"], 4)} for p in parts[0]]
    xs = [p["x"] for part in parts for p in part]
    ys = [p["y"] for part in parts for p in part]
    left, right, top, bottom = (round(v, 4) for v in (min(xs), max(xs), min(ys), max(ys)))
    return [{"x": left, "y": top}, {"x": right, "y": top}, {"x": right, "y": bottom}, {"x": left, "y": bottom}]


def _span_zone(lines: list[dict], start: int, end: int) -> tuple[str, list[dict]] | None:
    """The text of a span of the text of some lines (one per row) and where it is, or None when it lies on no line."""
    parts, offset = [], 0
    for line in lines:
        first, last = max(start - offset, 0), min(end - offset, len(line["text"]))
        if first < last and len(line["points"]) >= 4:
            parts.append(_part_of_line(line, first, last))
        offset += len(line["text"]) + 1  # the line break
    if not parts:
        return None
    return "\n".join(line["text"] for line in lines)[start:end].strip(), _zone(parts)


def find(pages: list[dict], entities: list[dict], model=None, threshold: float | None = None) -> list[dict]:
    """The elements found in the text of `pages` (`[{page, lines: [{text, points}]}]`) for `entities` (`[{id, name,
    definition, template_id}]`): one for each entity that was found, the likeliest, as `{page, entity_id, points, text,
    classifications}`. An entity that is not in the text is not in the answer."""
    if not entities or not any(page["lines"] for page in pages):
        return []
    model = model or get_model()
    threshold = config.GLINER_THRESHOLD if threshold is None else threshold
    by_label: dict[str, list[dict]] = {}
    for entity in entities:
        by_label.setdefault(label_of(entity), []).append(entity)

    best: dict[str, dict] = {}
    for page in pages:
        for lines in _chunks(page["lines"]):
            text = "\n".join(line["text"] for line in lines)
            for span in model.predict_entities(text, list(by_label), threshold=threshold):
                placed = _span_zone(lines, span["start"], span["end"])
                if placed is None or not placed[0]:
                    continue
                for entity in by_label.get(span["label"], []):
                    if entity["id"] not in best or span["score"] > best[entity["id"]]["score"]:
                        best[entity["id"]] = {
                            "score": float(span["score"]),
                            "page": page["page"],
                            "text": placed[0],
                            "zone": placed[1],
                            "entity": entity,
                        }

    return [
        {
            "page": found["page"],
            "entity_id": entity_id,
            "points": found["zone"],
            "text": found["text"],
            # As sure as GLiNER is of the span, the rest being « other ».
            "classifications": [
                {"template_id": found["entity"].get("template_id"), "confidence": round(found["score"], 6)},
                {"template_id": None, "confidence": round(1 - found["score"], 6)},
            ],
        }
        for entity_id, found in best.items()
    ]
