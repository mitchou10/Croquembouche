"""share a model

Revision ID: f3a1b5c7d9e0
Revises: e2f0a4b6c8d9
Create Date: 2026-11-10 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a1b5c7d9e0"
down_revision: str | Sequence[str] | None = "e2f0a4b6c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: every model that exists stays visible to everyone until its owner restricts it."""
    op.add_column("templates", sa.Column("visibility", sa.String(length=8), server_default="public", nullable=False))
    op.create_table(
        "template_shares",
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("value_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_template_shares_template_id"), "template_shares", ["template_id"], unique=False)
    op.create_index(op.f("ix_template_shares_value_hash"), "template_shares", ["value_hash"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_template_shares_value_hash"), table_name="template_shares")
    op.drop_index(op.f("ix_template_shares_template_id"), table_name="template_shares")
    op.drop_table("template_shares")
    op.drop_column("templates", "visibility")
