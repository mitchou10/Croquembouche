"""say the version a page was classified as

Revision ID: e6f4a8b0c2d3
Revises: d5e3f7a9b1c2
Create Date: 2026-11-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f4a8b0c2d3"
down_revision: str | Sequence[str] | None = "d5e3f7a9b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("page_classifications", sa.Column("template_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("page_classifications", "template_version")
