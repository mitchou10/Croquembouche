from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel

MAX_EXAMPLES = 5
MAX_TAGS = 10
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
    # Optional: what more the person has to say of the entity. A model that predates them has none.
    tags: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)]], Field(max_length=MAX_TAGS * 3)
    ] = []
    zone: Zone | None = None


class PageFields(CamelModel):
    """A name and a description of a page of a model's document; both are optional (without a name a page is the name
    of the model and its number)."""

    page: Annotated[int, Field(ge=1)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""


class TemplateFields(CamelModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""
    categories: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]], Field(max_length=30)
    ] = []
    entities: Annotated[list[EntityFields], Field(max_length=200)] = []
    pages: Annotated[list[PageFields], Field(max_length=200)] = []


class TemplateCreate(TemplateFields):
    document_id: str | None = None
    # The model this one is a sub-model of; absent for a root. A sub-model has no sub-model.
    parent_id: str | None = None


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


class TemplatePageOut(PageFields):
    # How the page is called: its name when it has one, else the name of the model and its number.
    label: str


class TemplateVersionOut(CamelModel):
    """A version of a model, X.Y.Z, as it was saved."""

    version: str
    date: date
    author_id: str
    author_name: str
    document: DocumentOut | None = None


class TemplateVersionDetail(TemplateVersionOut):
    """A version with everything the model was then."""

    fields: TemplateFields


class SubModelOut(CamelModel):
    """A sub-model, as its parent lists it."""

    id: str
    name: str
    version: str


class TemplateOut(CamelModel):
    id: str
    version: str
    # The model it is a sub-model of (and its name), or none for a root.
    parent_id: str | None = None
    parent_name: str | None = None
    # The sub-models of a root, by name; always empty for a sub-model.
    children: list[SubModelOut] = []
    owner_id: str
    owner_name: str
    name: str
    description: str
    categories: list[str]
    entities: list[EntityOut]
    # One per page of the document, with the default name filled in.
    pages: list[TemplatePageOut]
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
