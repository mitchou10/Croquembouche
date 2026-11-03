import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EncryptedText, TimestampMixin, UUIDMixin, utcnow
from app.models.document import Document
from app.models.user import UserProfile


class Analysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analyses"

    owner_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)

    owner: Mapped[UserProfile] = relationship(lazy="selectin")
    models: Mapped[list["AnalysisTemplate"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    shares: Mapped[list["AnalysisShare"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    runs: Mapped[list["Run"]] = relationship(
        order_by="Run.created_at.desc()", cascade="all, delete-orphan", lazy="selectin"
    )


class AnalysisTemplate(Base):
    __tablename__ = "analysis_templates"

    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id"), primary_key=True)


class AnalysisShare(UUIDMixin, Base):
    """Who an analysis is shared with: a person by e-mail address (personal data: encrypted) or a group by name. It is
    matched through `value_hash`, never by reading `value`."""

    __tablename__ = "analysis_shares"

    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # email, group
    value: Mapped[str] = mapped_column("value_encrypted", EncryptedText)
    value_hash: Mapped[str] = mapped_column(String(64), index=True)


class Run(UUIDMixin, Base):
    """One use of an analysis. Its results are for the person who ran it alone."""

    __tablename__ = "runs"

    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running, done, failed
    matches: Mapped[int] = mapped_column(Integer, default=0)
    file_name: Mapped[str | None] = mapped_column("file_name_encrypted", EncryptedText)
    screenshot_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    file_decision: Mapped[str | None] = mapped_column(String(8))  # kept, deleted
    page_review_status: Mapped[str] = mapped_column(String(16), default="pending")
    page_review_template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    user: Mapped[UserProfile] = relationship(lazy="selectin")
    screenshot: Mapped[Document | None] = relationship(lazy="selectin")
    page_classifications: Mapped[list["PageClassification"]] = relationship(
        order_by="PageClassification.confidence.desc()", cascade="all, delete-orphan", lazy="selectin"
    )
    detections: Mapped[list["Detection"]] = relationship(
        order_by="Detection.position", cascade="all, delete-orphan", lazy="selectin"
    )


class PageClassification(UUIDMixin, Base):
    """Which model the page as a whole could be; no template is « other »."""

    __tablename__ = "page_classifications"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"))
    confidence: Mapped[float] = mapped_column(Float)


class Detection(UUIDMixin, Base):
    __tablename__ = "detections"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    zone_page: Mapped[int] = mapped_column(Integer)
    zone_points: Mapped[list[dict[str, float]]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(8), default="analysis")  # analysis, manual
    review_status: Mapped[str] = mapped_column(String(16), default="pending")
    review_template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
    # Reading order for what the analysis found; what was added by hand comes after.
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    classifications: Mapped[list["DetectionClassification"]] = relationship(
        order_by="DetectionClassification.confidence.desc()", cascade="all, delete-orphan", lazy="selectin"
    )


class DetectionClassification(UUIDMixin, Base):
    __tablename__ = "detection_classifications"

    detection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"))
    confidence: Mapped[float] = mapped_column(Float)
