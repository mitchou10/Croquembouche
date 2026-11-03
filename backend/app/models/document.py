from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EncryptedText, TimestampMixin, UUIDMixin


class Document(UUIDMixin, TimestampMixin, Base):
    """An uploaded image or PDF; the file and the screenshots of its pages are in the store, under `storage_prefix`."""

    __tablename__ = "documents"

    owner_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), index=True)
    # A file name often holds a name or a case number: encrypted.
    name: Mapped[str] = mapped_column("name_encrypted", EncryptedText)
    content_type: Mapped[str] = mapped_column(String(64))
    pages: Mapped[int] = mapped_column(Integer)
    storage_prefix: Mapped[str] = mapped_column(String(255), unique=True)
