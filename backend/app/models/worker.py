from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, utcnow


class WorkerHeartbeat(Base):
    """A running instance of a worker, and when it last said it was alive. It registers its tasks when it starts, then
    says so every few seconds: one that has not for a while is down (its tasks are kept, offline, for a few days)."""

    __tablename__ = "worker_heartbeats"

    # Made by the instance, new at each start: two processes of one worker are two instances.
    instance_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    # Which worker it is an instance of (« template_matching », « ocr »...), and where it runs.
    service: Mapped[str] = mapped_column(String(64), default="", server_default="")
    hostname: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, index=True
    )

    tasks: Mapped[list["WorkerTask"]] = relationship(
        order_by="WorkerTask.name", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkerTask(UUIDMixin, Base):
    """A task an instance of a worker can be given: what it is called, in which version, what it takes (`input_schema`),
    what can be set (`parameters`) and what it gives (`output_schema`), as JSON Schemas."""

    __tablename__ = "worker_tasks"
    __table_args__ = (UniqueConstraint("name", "version", "instance_id"),)

    name: Mapped[str] = mapped_column(String(200), index=True)
    version: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    author: Mapped[str] = mapped_column(String(200), default="", server_default="")
    instance_id: Mapped[str] = mapped_column(
        ForeignKey("worker_heartbeats.instance_id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)


__all__ = ["WorkerHeartbeat", "WorkerTask"]
