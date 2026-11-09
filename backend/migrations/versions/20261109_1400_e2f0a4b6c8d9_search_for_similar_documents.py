"""search for similar documents

Revision ID: e2f0a4b6c8d9
Revises: d1e9f3a5b7c8
Create Date: 2026-11-09 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e2f0a4b6c8d9"
down_revision: str | Sequence[str] | None = "d1e9f3a5b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "searches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("template_ids", postgresql.JSONB(), nullable=True),
        sa.Column("neighbours", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("links", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("energy_kwh", sa.Float(), nullable=True),
        sa.Column("co2_kg", sa.Float(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_searches_user_id"), "searches", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_searches_user_id"), table_name="searches")
    op.drop_table("searches")
