"""pin a version of a model

Revision ID: a4b2c6d8e0f1
Revises: f3a1b5c7d9e0
Create Date: 2026-11-10 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b2c6d8e0f1"
down_revision: str | Sequence[str] | None = "f3a1b5c7d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: the analyses that exist keep following their models."""
    op.add_column("analysis_templates", sa.Column("version", sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("analysis_templates", "version")
