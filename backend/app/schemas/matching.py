"""What the worker hands back for a use: how each page of the document was classified, and the elements found."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalogue import Point


class PageClass(BaseModel):
    template_id: str | None = None
    template_page: int | None = None
    # The version (X.Y.Z) of the model that the page looks like: a model is looked for in every X it has had.
    template_version: str | None = None
    confidence: float = Field(ge=0, le=1)


class PageAnswer(BaseModel):
    page: int = Field(ge=1)
    classifications: list[PageClass]


class FoundClass(BaseModel):
    template_id: str | None = None
    confidence: float = Field(ge=0, le=1)


class FoundElement(BaseModel):
    page: int = Field(ge=1)
    entity_id: uuid.UUID | None = None
    points: list[Point] = Field(min_length=3)
    classifications: list[FoundClass]


class Consumption(BaseModel):
    """What computing a use consumed: the electricity, the CO2 that made in the country, and how long it took."""

    energy_kwh: float = Field(ge=0)
    co2_kg: float = Field(ge=0)
    duration_s: float = Field(ge=0)


class MatchingResult(BaseModel):
    status: Literal["done", "failed"]
    consumption: Consumption | None = None
    pages: list[PageAnswer] = []
    found: list[FoundElement] = []


class OcrLine(BaseModel):
    """A line of text and where it is on the page as it was given: the four corners, from 0 to 1."""

    text: str
    score: float = Field(ge=0, le=1)
    points: list[Point]


class OcrPage(BaseModel):
    page: int = Field(ge=1)
    # How far the page was turned clockwise (0, 90, 180 or 270) when it was scanned: the lines are read upright.
    angle: int = 0
    lines: list[OcrLine]


class FoundInText(FoundElement):
    """An element found in the text, for an entity that has no zone to carry over: where, and what was found there."""

    text: str


class OcrResult(BaseModel):
    """What the OCR worker hands back for a use: the text of each page, and what reading it consumed."""

    status: Literal["done", "failed"]
    consumption: Consumption | None = None
    pages: list[OcrPage] = []


class FindResult(BaseModel):
    """What the GLiNER worker hands back for a use: the elements it found in the text, and what it consumed."""

    status: Literal["done", "failed"]
    consumption: Consumption | None = None
    found: list[FoundInText] = []


class FoundNeighbourResult(BaseModel):
    template_id: str
    template_page: int = Field(ge=1)
    document_id: str
    similarity: float = Field(ge=0, le=1)


class FoundLink(BaseModel):
    source: str
    target: str
    similarity: float = Field(ge=0, le=1)


class SearchResult(BaseModel):
    """What the worker hands back for a search for similar documents: the pages of models that look like each page of
    the document, how they are linked, and what it consumed. A source is `page-N`; a neighbour is `<model>:<page>`."""

    status: Literal["done", "failed"]
    consumption: Consumption | None = None
    neighbours: list[FoundNeighbourResult] = []
    links: list[FoundLink] = []
