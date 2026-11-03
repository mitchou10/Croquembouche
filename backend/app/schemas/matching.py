"""What the worker hands back for a use: how each page of the document was classified, and the elements found."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalogue import Point


class PageClass(BaseModel):
    template_id: str | None = None
    template_page: int | None = None
    confidence: float = Field(ge=0, le=1)


class PageAnswer(BaseModel):
    page: int = Field(ge=1)
    classifications: list[PageClass]


class FoundClass(BaseModel):
    template_id: str | None = None
    confidence: float = Field(ge=0, le=1)


class FoundElement(BaseModel):
    page: int = Field(ge=1)
    points: list[Point] = Field(min_length=3)
    classifications: list[FoundClass]


class MatchingResult(BaseModel):
    status: Literal["done", "failed"]
    pages: list[PageAnswer] = []
    found: list[FoundElement] = []
