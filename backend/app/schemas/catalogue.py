from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel

MAX_EXAMPLES = 5
MAX_COMMENT_LENGTH = 500

Coordinate = Annotated[float, Field(ge=0, le=1)]
Example = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]


class Point(CamelModel):
    x: Coordinate
    y: Coordinate


class Zone(CamelModel):
    """Fractions (0 to 1) of the page, so that a zone does not depend on the size it is shown at."""

    page: Annotated[int, Field(ge=1)]
    points: Annotated[list[Point], Field(min_length=3, max_length=200)]


class EntityFields(CamelModel):
    # The id of an entity the model already has; anything else (a new entity) gets one when it is saved.
    id: str | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    definition: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""
    type: str
    examples: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]], Field(max_length=50)
    ] = []
    zone: Zone | None = None


class TemplateFields(CamelModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""
    categories: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]], Field(max_length=30)
    ] = []
    entities: Annotated[list[EntityFields], Field(max_length=200)] = []


class TemplateCreate(TemplateFields):
    document_id: str | None = None


class TemplateUpdate(TemplateFields):
    """`document_id`: absent keeps the document, null removes it, an id replaces it."""

    document_id: str | None = None


class SuggestionCreate(CamelModel):
    fields: TemplateFields
    message: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""


class Decision(CamelModel):
    accept: bool


class CommentCreate(CamelModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_COMMENT_LENGTH)]


class DocumentOut(CamelModel):
    id: str
    name: str
    content_type: str
    pages: int


class EntityOut(EntityFields):
    id: str
    stars: list[str]


class CommentOut(CamelModel):
    id: str
    author_id: str
    author_name: str
    text: str
    date: date


class SuggestionOut(CamelModel):
    id: str
    author_id: str
    author_name: str
    fields: TemplateFields
    message: str
    date: date
    status: str
    comments: list[CommentOut]
    stars: list[str]


class TemplateOut(CamelModel):
    id: str
    owner_id: str
    owner_name: str
    name: str
    description: str
    categories: list[str]
    entities: list[EntityOut]
    stars: list[str]
    suggestions: list[SuggestionOut]
    document: DocumentOut | None = None


class SuggestedEntity(CamelModel):
    """An entity a document suggests by itself, with where it is: to be taken as it is or changed."""

    name: str
    type: str
    zone: Zone
    # Where the suggestion comes from: a form field, a drawn box, or a blank to write on.
    source: Literal["widget", "box", "blank"]


class EntityTypeOut(CamelModel):
    value: str
    label: str
    definition: str
