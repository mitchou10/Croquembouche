"""read the text of a document

Revision ID: c0d8e2f4a6b7
Revises: b9c7d1e3f5a6
Create Date: 2026-11-07 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0d8e2f4a6b7"
down_revision: str | Sequence[str] | None = "b9c7d1e3f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # « none » for the uses from before: the text of their document was never read.
    op.add_column("runs", sa.Column("ocr_status", sa.String(16), server_default="none", nullable=False))
    op.add_column("runs", sa.Column("ocr_encrypted", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("runs", "ocr_encrypted")
    op.drop_column("runs", "ocr_status")
