from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EncryptedText


class UserProfile(Base):
    """What is known of a person beyond their Keycloak identifier, to show who made what. The name and the address are
    personal data: encrypted, and the address is looked up by its blind index (to resolve a share made to it)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # the `sub` of Keycloak
    display_name: Mapped[str | None] = mapped_column("display_name_encrypted", EncryptedText)
    email: Mapped[str | None] = mapped_column("email_encrypted", EncryptedText)
    email_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
