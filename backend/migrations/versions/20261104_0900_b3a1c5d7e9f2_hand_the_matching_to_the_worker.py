"""hand the matching to the worker

Revision ID: b3a1c5d7e9f2
Revises: a148c6afa9ec
Create Date: 2026-11-04 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a1c5d7e9f2"
down_revision: str | Sequence[str] | None = "a148c6afa9ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("runs", sa.Column("matching_document_id", sa.Uuid(), nullable=True))
    op.add_column("runs", sa.Column("keep_screenshot", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_foreign_key(
        "runs_matching_document_id_fkey", "runs", "documents", ["matching_document_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("runs_matching_document_id_fkey", "runs", type_="foreignkey")
    op.drop_column("runs", "keep_screenshot")
    op.drop_column("runs", "matching_document_id")
