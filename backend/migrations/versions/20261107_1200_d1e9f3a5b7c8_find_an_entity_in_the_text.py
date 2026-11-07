"""find an entity in the text

Revision ID: d1e9f3a5b7c8
Revises: c0d8e2f4a6b7
Create Date: 2026-11-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d1e9f3a5b7c8"
down_revision: str | Sequence[str] | None = "c0d8e2f4a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("detections", sa.Column("found_in_text", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("detections", sa.Column("text_encrypted", sa.LargeBinary(), nullable=True))
    # The GLiNER worker finds them in the text the OCR read: « none » for the uses that had nothing to find.
    op.add_column("runs", sa.Column("find_status", sa.String(16), server_default="none", nullable=False))
    op.add_column("runs", sa.Column("find_entities", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("runs", "find_entities")
    op.drop_column("runs", "find_status")
    op.drop_column("detections", "text_encrypted")
    op.drop_column("detections", "found_in_text")
