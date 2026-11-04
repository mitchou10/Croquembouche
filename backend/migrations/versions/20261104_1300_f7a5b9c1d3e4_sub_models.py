"""sub-models

Revision ID: f7a5b9c1d3e4
Revises: e6f4a8b0c2d3
Create Date: 2026-11-04 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a5b9c1d3e4"
down_revision: str | Sequence[str] | None = "e6f4a8b0c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("templates", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_templates_parent_id"), "templates", ["parent_id"], unique=False)
    op.create_foreign_key("templates_parent_id_fkey", "templates", "templates", ["parent_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("templates_parent_id_fkey", "templates", type_="foreignkey")
    op.drop_index(op.f("ix_templates_parent_id"), table_name="templates")
    op.drop_column("templates", "parent_id")
