import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, utcnow
from app.models.document import Document


class Search(UUIDMixin, Base):
    """A search for the documents that look like one that was sent: the pages of models of the catalogue that look the
    most like each of its pages. A worker computes it, so it is first running. It is kept, with the document (its pages
    are what is shown), to be opened again, and what it consumed is counted in the person's own."""

    __tablename__ = "searches"

    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), index=True)
    # The document that was sent: its pages are in the store, and it goes with the search.
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running, done, failed
    # How many neighbours were asked for, for each page, and in which models: none is every model.
    k: Mapped[int] = mapped_column(Integer)
    template_ids: Mapped[list[str] | None] = mapped_column(JSONB)
    # What the worker found: `[{id, template_id, template_page, document_id, similarity}]` and
    # `[{source, target, similarity}]` (a source is `page-N`, a page of the document, or a neighbour).
    neighbours: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    links: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    # What computing it consumed, as the worker measured it (CodeCarbon): none when it was not measured.
    energy_kwh: Mapped[float | None] = mapped_column(Float)
    co2_kg: Mapped[float | None] = mapped_column(Float)
    duration_s: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    document: Mapped[Document | None] = relationship(lazy="selectin")
