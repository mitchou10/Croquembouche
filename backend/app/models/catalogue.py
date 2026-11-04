import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow
from app.models.document import Document
from app.models.user import UserProfile


class EntityType(Base):
    """A kind of value an entity can be (text, date, amount...): a fixed list, with the definition shown to people."""

    __tablename__ = "entity_types"

    value: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    definition: Mapped[str] = mapped_column(Text)


class Category(UUIDMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(64), unique=True)


class Template(UUIDMixin, TimestampMixin, Base):
    """A model of the catalogue: what to look for, with an optional example document."""

    __tablename__ = "templates"

    owner_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    # A sub-model points to the model it is under; a root has none. One level only: a sub-model has no sub-model (kept
    # by the service). A sub-model is a model like any other, with its own entities, document and version.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id"), index=True)
    # X.Y.Z: X goes up when the example document changes, Y when what describes the model does (name, description,
    # categories, notes of pages), Z when its entities do. Each bump keeps a snapshot (see `TemplateVersion`).
    major: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    minor: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    patch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    owner: Mapped[UserProfile] = relationship(lazy="selectin")
    document: Mapped[Document | None] = relationship(lazy="selectin")
    categories: Mapped[list["Category"]] = relationship(
        secondary="template_categories", order_by="Category.name", lazy="selectin"
    )
    entities: Mapped[list["TemplateEntity"]] = relationship(
        order_by="TemplateEntity.position", cascade="all, delete-orphan", lazy="selectin"
    )
    stars: Mapped[list["TemplateStar"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    page_notes: Mapped[list["TemplatePage"]] = relationship(
        order_by="TemplatePage.page", cascade="all, delete-orphan", lazy="selectin"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        order_by="Suggestion.created_at.desc()", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def version(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class TemplateVersion(UUIDMixin, Base):
    """The model as it became at a version, kept whole: to read an old version, to go back to it, and to look in the
    image it had. The versions that share an X share one stored document."""

    __tablename__ = "template_versions"
    __table_args__ = (UniqueConstraint("template_id", "major", "minor", "patch"),)

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    major: Mapped[int] = mapped_column(Integer)
    minor: Mapped[int] = mapped_column(Integer)
    patch: Mapped[int] = mapped_column(Integer)
    # The fields as `TemplateFields` has them (entities with their ids and zones, pages that were given something).
    snapshot: Mapped[dict] = mapped_column(JSONB)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    author: Mapped[UserProfile] = relationship(lazy="selectin")
    document: Mapped[Document | None] = relationship(lazy="selectin")

    @property
    def version(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class TemplateCategory(Base):
    __tablename__ = "template_categories"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)


class TemplateEntity(UUIDMixin, Base):
    __tablename__ = "template_entities"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    definition: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(ForeignKey("entity_types.value"))
    examples: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Where it appears on the example document: the page (from 1) and a polygon, in fractions (0 to 1) of the page.
    zone_page: Mapped[int | None] = mapped_column(Integer)
    zone_points: Mapped[list[dict[str, float]] | None] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer, default=0)

    stars: Mapped[list["EntityStar"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class TemplatePage(Base):
    """A name and a description of a page of a model's document: only for a page that was given something. Without one
    a page is the name of the model and its number."""

    __tablename__ = "template_pages"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True)
    page: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class TemplateStar(Base):
    __tablename__ = "template_stars"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), primary_key=True)


class EntityStar(Base):
    __tablename__ = "entity_stars"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_entities.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), primary_key=True)


class Suggestion(UUIDMixin, Base):
    """A change proposed by someone other than the owner, kept whole (the fields as they would become)."""

    __tablename__ = "suggestions"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"))
    fields: Mapped[dict] = mapped_column(JSONB)
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending, accepted, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    author: Mapped[UserProfile] = relationship(lazy="selectin")
    stars: Mapped[list["SuggestionStar"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    comments: Mapped[list["SuggestionComment"]] = relationship(
        order_by="SuggestionComment.created_at", cascade="all, delete-orphan", lazy="selectin"
    )


class SuggestionStar(Base):
    __tablename__ = "suggestion_stars"

    suggestion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suggestions.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), primary_key=True)


class SuggestionComment(UUIDMixin, Base):
    __tablename__ = "suggestion_comments"

    suggestion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suggestions.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    author: Mapped[UserProfile] = relationship(lazy="selectin")
