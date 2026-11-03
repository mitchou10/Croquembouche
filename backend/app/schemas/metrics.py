from app.schemas.base import CamelModel


class Quality(CamelModel):
    """How right the analysis has been, as far as people have said so: it grows with every prediction looked at.

    `correct` and `wrong` are the predictions someone decided on (validated or annotated with this very model, against
    invalidated or annotated with another); `pending` are the ones nobody has looked at yet; `missed` are what people
    found that the analysis did not (added by hand, or annotated as this model on a prediction of another)."""

    reviewed: int
    pending: int
    correct: int
    wrong: int
    missed: int
    precision: float | None
    recall: float | None
    f1: float | None
    # How sure the analysis was, on average, of what turned out right and of what turned out wrong: far apart is a
    # confidence that means something.
    mean_confidence_correct: float | None
    mean_confidence_wrong: float | None


class PageQuality(Quality):
    # Of the pages rightly taken for a page of this model, the share whose page of the model was right too.
    exact: float | None


class EntityQuality(Quality):
    id: str
    name: str


class TemplateMetrics(CamelModel):
    """The quality of the analysis on one model: its pages, its elements, and each of its entities."""

    pages: PageQuality
    elements: Quality
    entities: list[EntityQuality]
