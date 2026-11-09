from datetime import datetime
from typing import Literal

from app.schemas.analysis import ConsumptionOut
from app.schemas.base import CamelModel

# The most neighbours a page can ask for, and how many it does when it does not say.
MAX_NEIGHBOURS = 12
DEFAULT_NEIGHBOURS = 6


class NeighbourOut(CamelModel):
    """A page of a model of the catalogue that looks like a page of the document. `document_id` is the example document
    of the model that was looked at (a model has had several: each version X has its own), to show the right image."""

    id: str
    template_id: str
    template_page: int
    document_id: str
    # 0 to 1: how much it looks like the page of the document it looks the most like.
    similarity: float


class LinkOut(CamelModel):
    """A link between two nodes: `page-N` is the page N of the document, any other is a neighbour (`<model>:<page>`)."""

    source: str
    target: str
    similarity: float


class SearchSummaryOut(CamelModel):
    id: str
    file_name: str
    status: Literal["running", "done", "failed"]
    k: int
    # The models looked in, or none for every model.
    template_ids: list[str] | None
    created_at: datetime
    pages: int
    neighbour_count: int
    # Absent when it was not measured (or has not ended).
    consumption: ConsumptionOut | None = None


class SearchOut(SearchSummaryOut):
    neighbours: list[NeighbourOut]
    links: list[LinkOut]
