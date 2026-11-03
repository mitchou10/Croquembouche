import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, LargeBinary, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core import crypto


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Set by the application, not by the database: `now()` is the start of the transaction, the same for everything
    written in it, which would leave newest-first orders to chance."""
    return datetime.now(UTC)


class EncryptedText(TypeDecorator):
    """Text kept encrypted (Fernet) in a `bytea` column: the code reads and writes plain strings."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> bytes | None:
        return None if value is None else crypto.encrypt(value)

    def process_result_value(self, value: bytes | None, dialect) -> str | None:
        return None if value is None else crypto.decrypt(value)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, onupdate=utcnow
    )
