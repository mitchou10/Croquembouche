from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel
from app.schemas.catalogue import DocumentOut, Zone

MAX_SHARES = 20

ReviewStatus = Literal["pending", "validated", "invalidated", "annotated"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
ShareValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]


class Share(CamelModel):
    """Who an analysis is shared with: a person, by e-mail address, or a group, by name."""

    kind: Literal["email", "group"]
    value: ShareValue


class AnalysisCreate(CamelModel):
    name: Name
    description: Description = ""
    template_ids: Annotated[list[str], Field(min_length=1, max_length=100)]
    is_public: bool = False
    shares: Annotated[list[Share], Field(max_length=MAX_SHARES)] = []


class Review(CamelModel):
    """What the person decides of a prediction. `annotated` names the model it is, one of the analysis, and for the
    classification of a page the page of that model (when it has several)."""

    status: ReviewStatus
    template_id: str | None = None
    template_page: int | None = None


class ElementCreate(CamelModel):
    zone: Zone
    template_id: str
    # Which entity of the model it is, when the person knows: what the recall of each entity is measured on.
    entity_id: str | None = None


class FileDecision(CamelModel):
    decision: Literal["kept", "deleted"]


class ClassificationOut(CamelModel):
    """What something could be, and how sure the analysis is (0 to 1); no model is « other ». For a page of the
    document, the page of the model it looks like (« form X, page 3 »)."""

    template_id: str | None
    template_page: int | None = None
    confidence: float


class ReviewOut(CamelModel):
    status: ReviewStatus
    template_id: str | None = None
    template_page: int | None = None


class DetectionOut(CamelModel):
    id: str
    zone: Zone
    classifications: list[ClassificationOut]
    review: ReviewOut
    source: Literal["analysis", "manual"]
    entity_id: str | None = None


class PageOut(CamelModel):
    """What one page of the document tried could be, and what was decided of it."""

    page: int
    classifications: list[ClassificationOut]
    review: ReviewOut


class RunOut(CamelModel):
    """One use of an analysis. Whoever can open the analysis sees who ran it, when and how it went; what it found is for
    the person who ran it alone, an administrator included."""

    id: str
    user_id: str
    user_name: str
    date: date
    status: Literal["running", "done", "failed"]
    matches: int
    # Whether the use was tried on a document, so has a result: said to everyone, shown to its person alone.
    has_result: bool
    file_name: str | None = None
    detections: list[DetectionOut] | None = None
    pages: list[PageOut] | None = None
    screenshot: DocumentOut | None = None
    file_decision: Literal["kept", "deleted"] | None = None


class AnalysisOut(CamelModel):
    """An analysis. One the person cannot open is only named, with its date and how it is going: the rest (who made it,
    what it is for, its uses, its recipients) is empty."""

    id: str
    can_open: bool
    name: str
    description: str
    owner_id: str
    owner_name: str
    views: int
    runs: list[RunOut]
    template_ids: list[str]
    is_public: bool
    # Only for the owner (and an administrator): the people it is shared with are not for everyone to see.
    shares: list[Share]
    date: date
    status: Literal["running", "done", "failed"]
    matches: int


class ViewsOut(CamelModel):
    views: int


class GroupOut(CamelModel):
    id: str
    name: str
