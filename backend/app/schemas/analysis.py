from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel
from app.schemas.catalogue import DocumentOut, Zone
from app.schemas.matching import OcrPage

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
    # The version (X.Y.Z) of the model the page looks like: the page above is a page of that version.
    template_version: str | None = None
    confidence: float


class ReviewOut(CamelModel):
    status: ReviewStatus
    template_id: str | None = None
    template_page: int | None = None


class ConsumptionOut(CamelModel):
    """What computing something consumed: the electricity (Wh), the CO2 it made (g), the water it cost (mL, estimated
    from the electricity) and the time it took (s)."""

    duration_s: float = 0
    energy_wh: float = 0
    co2_g: float = 0
    water_ml: float = 0


class DetectionOut(CamelModel):
    id: str
    zone: Zone
    classifications: list[ClassificationOut]
    review: ReviewOut
    source: Literal["analysis", "manual"]
    entity_id: str | None = None
    # Found in the text, by the definition of its entity, instead of by a zone of a model.
    found_in_text: bool = False
    # The text the OCR read in the zone: only when a single use is asked for, once it is read, and never for an image or
    # a table. Absent until then.
    text: str | None = None


class PageOut(CamelModel):
    """What one page of the document tried could be, and what was decided of it."""

    page: int
    classifications: list[ClassificationOut]
    review: ReviewOut


class AnalysisConsumptionOut(CamelModel):
    """What the uses of a person consumed in one analysis. `measured` are the uses that were (the others add
    nothing)."""

    id: str
    name: str
    uses: int
    measured: int
    consumption: ConsumptionOut


class SearchesConsumptionOut(CamelModel):
    """What the searches for similar documents of a person consumed: how many, how many were measured (the others add
    nothing), and what."""

    count: int
    measured: int
    consumption: ConsumptionOut


class MyConsumptionOut(CamelModel):
    """What all the uses of a person consumed, and the detail by analysis, the most consuming first; and, apart, what
    their searches for similar documents consumed."""

    uses: int
    measured: int
    consumption: ConsumptionOut
    analyses: list[AnalysisConsumptionOut]
    searches: SearchesConsumptionOut


class RunOut(CamelModel):
    """One use of an analysis. Whoever can open the analysis sees who ran it, when and how it went; what it found is for
    the person who ran it alone, an administrator included."""

    id: str
    user_id: str
    user_name: str
    date: date
    status: Literal["running", "done", "failed", "cancelled"]
    matches: int
    # Absent when the use was not measured (or has not ended).
    consumption: ConsumptionOut | None = None
    # The version (X.Y.Z) of each model of the analysis, by id, when the use started.
    template_versions: dict[str, str] = {}
    # Whether the use was tried on a document, so has a result: said to everyone, shown to its person alone.
    has_result: bool
    file_name: str | None = None
    detections: list[DetectionOut] | None = None
    pages: list[PageOut] | None = None
    screenshot: DocumentOut | None = None
    file_decision: Literal["kept", "deleted"] | None = None
    # The text of the document comes after the matching, once the OCR has read it: say so, then give it (only when a
    # single use is asked for; it is the person's alone).
    ocr_status: Literal["none", "running", "done", "failed"] = "none"
    # Whether the entities with no zone are found in that text: waiting for it to be read, being found, are, or could
    # not be.
    find_status: Literal["none", "waiting", "running", "done", "failed"] = "none"
    ocr: list[OcrPage] | None = None


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
    # What all its measured uses consumed.
    consumption: ConsumptionOut = ConsumptionOut()


class ViewsOut(CamelModel):
    views: int


class GroupOut(CamelModel):
    id: str
    name: str
