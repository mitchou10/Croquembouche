"""The entities a PDF suggests by itself, with their zones.

A fillable form (AcroForm) names its fields and says where they are. Any other PDF has what is drawn on it: empty boxes
and blanks (a line to write on) that the text next to them names. Both are far more exact than looking at a picture, so
they come first; scans and images have nothing of the sort and suggest nothing here.

PyMuPDF gives the widgets, the words and the drawings in the page *as it is stored*, while the screenshots (and the
zones people draw) are of the page *as it is shown*, rotated: the rectangles are brought to the latter before they are
sent."""

import re
from dataclasses import dataclass
from typing import Literal

import pymupdf

Source = Literal["widget", "box", "blank"]

MAX_SUGGESTIONS = 100
# A blank is a line long enough to write on; a box is big enough to hold something and not a whole table.
MIN_BLANK = 40
MIN_BOX_WIDTH = 20
MIN_BOX_HEIGHT = 8
MAX_BOX_HEIGHT = 60
# A square this small is a check box, not a field.
CHECK_BOX = (6, 18)
# How high the writing above a blank is taken to be, when the label does not say.
DEFAULT_LINE_HEIGHT = 14
# The words of a label are one phrase while they are no further apart than this.
LABEL_GAP = 14
LABEL_REACH = 120
OVERLAP = 0.6

_TYPE_HINTS = (
    ("date", re.compile(r"\bdate\b|\bné(e)? le\b|\bfait le\b", re.I)),
    ("amount", re.compile(r"montant|€|euros?\b|\bsomme\b|\bprix\b|\btotal\b", re.I)),
    ("percentage", re.compile(r"%|\btaux\b|pourcentage", re.I)),
)


@dataclass
class Suggestion:
    name: str
    type: str
    page: int
    points: list[dict[str, float]]
    source: Source


@dataclass
class _Candidate:
    """A place where something is written, in the stored coordinates of its page."""

    rect: pymupdf.Rect
    page: int
    source: Source
    name: str = ""
    type: str = "text"
    label_side: Literal["left", "right"] = "left"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" :. -_…")[:200]


def _type_for(label: str, default: str = "text") -> str:
    for kind, pattern in _TYPE_HINTS:
        if pattern.search(label):
            return kind
    return default


def _zone(rect: pymupdf.Rect, page: pymupdf.Page) -> list[dict[str, float]]:
    """The four corners of the rectangle as fractions of the page as it is shown, top left first."""
    shown = pymupdf.Rect(rect) * page.rotation_matrix
    width, height = page.rect.width, page.rect.height

    def fraction(value: float, size: float) -> float:
        return round(min(max(value / size, 0.0), 1.0), 4)

    left, right = fraction(shown.x0, width), fraction(shown.x1, width)
    top, bottom = fraction(shown.y0, height), fraction(shown.y1, height)
    return [{"x": left, "y": top}, {"x": right, "y": top}, {"x": right, "y": bottom}, {"x": left, "y": bottom}]


def _overlap(a: pymupdf.Rect, b: pymupdf.Rect) -> float:
    """How much of the smaller rectangle the other covers (0 to 1)."""
    common = pymupdf.Rect(a) & b
    if common.is_empty:
        return 0.0
    smaller = min(a.get_area(), b.get_area()) or 1.0
    return common.get_area() / smaller


# ------------------------------------------------------------------------------------------------ labels


def _words(page: pymupdf.Page) -> list[tuple[pymupdf.Rect, str]]:
    return [(pymupdf.Rect(w[:4]), w[4]) for w in page.get_text("words")]


def _on_the_same_line(rect: pymupdf.Rect, word: pymupdf.Rect) -> bool:
    middle = (word.y0 + word.y1) / 2
    return rect.y0 - 3 <= middle <= rect.y1 + 3


def _label_to_the_left(rect: pymupdf.Rect, words: list[tuple[pymupdf.Rect, str]]) -> str:
    """The phrase that ends at the left of the rectangle, on its line."""
    line = sorted(
        (w for w in words if _on_the_same_line(rect, w[0]) and w[0].x1 <= rect.x0 + 2),
        key=lambda w: -w[0].x1,
    )
    chain: list[tuple[pymupdf.Rect, str]] = []
    edge = rect.x0
    for word in line:
        # The label may stand some way from the field; its own words are close to one another.
        if edge - word[0].x1 > (LABEL_GAP if chain else LABEL_REACH):
            break
        chain.append(word)
        edge = word[0].x0
    return _clean(" ".join(text for _, text in reversed(chain)))


def _label_to_the_right(rect: pymupdf.Rect, words: list[tuple[pymupdf.Rect, str]]) -> str:
    line = sorted(
        (w for w in words if _on_the_same_line(rect, w[0]) and w[0].x0 >= rect.x1 - 2),
        key=lambda w: w[0].x0,
    )
    chain: list[tuple[pymupdf.Rect, str]] = []
    edge = rect.x1
    for word in line:
        if word[0].x0 - edge > (LABEL_GAP if chain else LABEL_REACH):
            break
        chain.append(word)
        edge = word[0].x1
    return _clean(" ".join(text for _, text in chain))


def _label_above(rect: pymupdf.Rect, words: list[tuple[pymupdf.Rect, str]]) -> str:
    """The line of text just above the rectangle, over its width: the caption of a box under its title."""
    above = [
        w
        for w in words
        if w[0].y1 <= rect.y0 + 2 and rect.y0 - w[0].y1 < 18 and w[0].x0 < rect.x1 and w[0].x1 > rect.x0
    ]
    if not above:
        return ""
    bottom = max(w[0].y1 for w in above)
    line = sorted((w for w in above if bottom - w[0].y1 < 4), key=lambda w: w[0].x0)
    return _clean(" ".join(text for _, text in line))


def _label_for(candidate: _Candidate, words: list[tuple[pymupdf.Rect, str]]) -> str:
    order = (
        (_label_to_the_right, _label_to_the_left)
        if candidate.label_side == "right"
        else (_label_to_the_left, _label_above)
    )
    for find in order:
        label = find(candidate.rect, words)
        if label:
            return label
    return ""


# ------------------------------------------------------------------------------------------------ widgets

_CHECKS = {pymupdf.PDF_WIDGET_TYPE_CHECKBOX}
_CHOICES = {pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON}


def _widget_type(widget: pymupdf.Widget, label: str) -> str:
    if widget.field_type in _CHECKS:
        return "yes_no"
    if widget.field_type == pymupdf.PDF_WIDGET_TYPE_TEXT:
        if widget.text_format == pymupdf.PDF_WIDGET_TX_FORMAT_DATE:
            return "date"
        if widget.text_format == pymupdf.PDF_WIDGET_TX_FORMAT_NUMBER:
            return "decimal"
    return _type_for(label)


def _field_name(widget: pymupdf.Widget) -> str:
    """What the form calls the field when it has no label: the last part of its name, without the form's own noise
    (« topmostSubform[0].Page1[0].Nom[0] » is « Nom »)."""
    last = (widget.field_name or "").split(".")[-1]
    return _clean(re.sub(r"\[\d+\]", "", last).replace("_", " "))


def _from_widgets(page: pymupdf.Page, number: int, words: list[tuple[pymupdf.Rect, str]]) -> list[_Candidate]:
    groups: dict[str, list[pymupdf.Widget]] = {}
    singles: list[pymupdf.Widget] = []
    for widget in page.widgets():
        rect = pymupdf.Rect(widget.rect)
        if rect.is_empty or rect.width < 4 or rect.height < 4:
            continue
        if widget.field_type in _CHOICES:
            groups.setdefault(widget.field_name or "", []).append(widget)
        elif widget.field_type != pymupdf.PDF_WIDGET_TYPE_BUTTON:  # a push button writes nothing
            singles.append(widget)

    found: list[_Candidate] = []
    for widget in singles:
        candidate = _Candidate(pymupdf.Rect(widget.rect), number, "widget")
        label = _clean(widget.field_label or "") or _label_for(candidate, words) or _field_name(widget)
        candidate.name = label
        candidate.type = _widget_type(widget, label)
        found.append(candidate)
    # The buttons of a radio group are one answer: one suggestion, over all of them.
    for widgets in groups.values():
        union = pymupdf.Rect(widgets[0].rect)
        for widget in widgets[1:]:
            union |= pymupdf.Rect(widget.rect)
        candidate = _Candidate(union, number, "widget")
        label = _field_name(widgets[0]) or _clean(widgets[0].field_label or "") or _label_for(candidate, words)
        candidate.name, candidate.type = label, _type_for(label)
        found.append(candidate)
    return found


# ------------------------------------------------------------------------------------------------ drawings


def _is_check_box(rect: pymupdf.Rect) -> bool:
    low, high = CHECK_BOX
    return low <= rect.width <= high and low <= rect.height <= high and abs(rect.width - rect.height) <= 3


def _holds_text(rect: pymupdf.Rect, words: list[tuple[pymupdf.Rect, str]]) -> bool:
    return any(_overlap(rect, w[0]) > 0.5 for w in words)


def _from_drawings(page: pymupdf.Page, number: int, words: list[tuple[pymupdf.Rect, str]]) -> list[_Candidate]:
    found: list[_Candidate] = []
    for drawing in page.get_drawings():
        if "s" not in drawing["type"]:  # a field is outlined; a plain fill is a background
            continue
        for item in drawing["items"]:
            if item[0] == "re":
                rect = pymupdf.Rect(item[1])
                if _is_check_box(rect):
                    found.append(_Candidate(rect, number, "box", type="yes_no", label_side="right"))
                elif (
                    rect.width >= MIN_BOX_WIDTH
                    and MIN_BOX_HEIGHT <= rect.height <= MAX_BOX_HEIGHT
                    and not _holds_text(rect, words)
                ):
                    found.append(_Candidate(rect, number, "box"))
            elif item[0] == "l":
                start, end = pymupdf.Point(item[1]), pymupdf.Point(item[2])
                if abs(start.y - end.y) <= 1.5 and abs(end.x - start.x) >= MIN_BLANK:
                    left, right = sorted((start.x, end.x))
                    # Writing sits on the line: the zone is the strip above it.
                    zone = pymupdf.Rect(left, start.y - DEFAULT_LINE_HEIGHT, right, start.y)
                    if not _holds_text(zone, words):  # a line under words is an underline, not a blank
                        found.append(_Candidate(zone, number, "blank"))
    return found


# ------------------------------------------------------------------------------------------------ the whole PDF

_PRIORITY = {"widget": 0, "box": 1, "blank": 2}


def _distinct(candidates: list[_Candidate]) -> list[_Candidate]:
    """What several things say of one place is said once, by the most reliable of them."""
    kept: list[_Candidate] = []
    for candidate in sorted(candidates, key=lambda c: _PRIORITY[c.source]):
        if not any(k.page == candidate.page and _overlap(k.rect, candidate.rect) >= OVERLAP for k in kept):
            kept.append(candidate)
    return kept


def suggest(data: bytes) -> list[Suggestion]:
    """The entities a PDF suggests, in reading order, at most `MAX_SUGGESTIONS`. Nothing for a PDF that cannot be read,
    or that has no field, no box and no blank (a text, a scan)."""
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        return []
    suggestions: list[Suggestion] = []
    with document:
        if document.needs_pass:
            return []
        for number, page in enumerate(document, start=1):
            words = _words(page)
            candidates = _distinct([*_from_widgets(page, number, words), *_from_drawings(page, number, words)])
            for candidate in sorted(candidates, key=lambda c: (round(c.rect.y0 / 6), c.rect.x0)):
                # A box or a blank nobody names is a decoration, or a cell of a table: only a label makes it a field.
                label = candidate.name or _label_for(candidate, words)
                if not label and candidate.source != "widget":
                    continue
                name = label or f"Champ {len(suggestions) + 1}"
                kind = candidate.type if candidate.type != "text" else _type_for(name)
                suggestions.append(Suggestion(name, kind, number, _zone(candidate.rect, page), candidate.source))
                if len(suggestions) >= MAX_SUGGESTIONS:
                    return suggestions
    return suggestions
