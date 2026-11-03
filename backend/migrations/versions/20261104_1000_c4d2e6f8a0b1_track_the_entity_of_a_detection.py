"""track the entity of a detection

Revision ID: c4d2e6f8a0b1
Revises: b3a1c5d7e9f2
Create Date: 2026-11-04 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d2e6f8a0b1"
down_revision: str | Sequence[str] | None = "b3a1c5d7e9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("detections", sa.Column("entity_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_detections_entity_id"), "detections", ["entity_id"], unique=False)
    op.create_foreign_key(
        "detections_entity_id_fkey", "detections", "template_entities", ["entity_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("detections_entity_id_fkey", "detections", type_="foreignkey")
    op.drop_index(op.f("ix_detections_entity_id"), table_name="detections")
    op.drop_column("detections", "entity_id")
