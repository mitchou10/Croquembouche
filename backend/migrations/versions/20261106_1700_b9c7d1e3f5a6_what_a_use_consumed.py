"""what a use consumed

Revision ID: b9c7d1e3f5a6
Revises: a8b6c0d2e4f5
Create Date: 2026-11-06 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c7d1e3f5a6"
down_revision: str | Sequence[str] | None = "a8b6c0d2e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # As the worker measured it (CodeCarbon); null for a use that was not measured, which the ones before are.
    op.add_column("runs", sa.Column("energy_kwh", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("co2_kg", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("duration_s", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("runs", "duration_s")
    op.drop_column("runs", "co2_kg")
    op.drop_column("runs", "energy_kwh")
