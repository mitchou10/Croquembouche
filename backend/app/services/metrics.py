"""How right the analysis is, from what people decide of its predictions (validate, invalidate, annotate).

There is no set of documents to measure against: the decisions are the ground truth, and the numbers grow with them. A
prediction is of one model (or of none), someone says it was right, wrong, or another model; a model nobody predicted
can still be found by hand. What is measured here is the same for a page, an element, and an entity."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    """A prediction, and what was decided of it (a page of the document, or an element found in it)."""

    top_template: uuid.UUID | None
    top_page: int | None
    confidence: float
    status: str  # pending, validated, invalidated, annotated
    review_template: uuid.UUID | None = None
    review_page: int | None = None
    source: str = "analysis"  # analysis, or manual for an element added by hand
    entity: uuid.UUID | None = None


@dataclass(frozen=True)
class Counts:
    reviewed: int
    pending: int
    correct: int
    wrong: int
    missed: int
    precision: float | None
    recall: float | None
    f1: float | None
    mean_confidence_correct: float | None
    mean_confidence_wrong: float | None


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _predicted(row: Row, template_id: uuid.UUID) -> bool:
    return row.source == "analysis" and row.top_template == template_id


def is_correct(row: Row, template_id: uuid.UUID) -> bool:
    """Validated, or annotated with the very model that was predicted (an element or a page of it)."""
    return row.status == "validated" or (row.status == "annotated" and row.review_template == template_id)


def count(rows: list[Row], template_id: uuid.UUID) -> Counts:
    """The quality of what was predicted as `template_id` among `rows`, and what was found of it that was not."""
    predicted = [r for r in rows if _predicted(r, template_id)]
    decided = [r for r in predicted if r.status != "pending"]
    right = [r for r in decided if is_correct(r, template_id)]
    wrong = [r for r in decided if not is_correct(r, template_id)]
    # Found by hand, or by annotating a prediction of another model: what the analysis did not see.
    missed = [
        r
        for r in rows
        if not _predicted(r, template_id) and r.status == "annotated" and r.review_template == template_id
    ]
    precision = _ratio(len(right), len(decided))
    recall = _ratio(len(right), len(right) + len(missed))
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else round(2 * precision * recall / (precision + recall), 4)
    )
    return Counts(
        reviewed=len(decided),
        pending=len(predicted) - len(decided),
        correct=len(right),
        wrong=len(wrong),
        missed=len(missed),
        precision=precision,
        recall=recall,
        f1=f1,
        mean_confidence_correct=_mean([r.confidence for r in right]),
        mean_confidence_wrong=_mean([r.confidence for r in wrong]),
    )


def exact_pages(rows: list[Row], template_id: uuid.UUID) -> float | None:
    """Of the pages rightly taken for a page of the model, the share whose page of the model was right too."""
    right = [r for r in rows if _predicted(r, template_id) and r.status != "pending" and is_correct(r, template_id)]
    exact = [r for r in right if r.status == "validated" or r.review_page == r.top_page]
    return _ratio(len(exact), len(right))


def entity_rows(rows: list[Row], entity: uuid.UUID) -> list[Row]:
    return [r for r in rows if r.entity == entity]
