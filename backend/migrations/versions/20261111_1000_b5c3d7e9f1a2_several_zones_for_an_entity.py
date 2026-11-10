"""several zones for an entity

Revision ID: b5c3d7e9f1a2
Revises: a4b2c6d8e0f1
Create Date: 2026-11-11 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b5c3d7e9f1a2"
down_revision: str | Sequence[str] | None = "a4b2c6d8e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: the zone an entity had becomes the first of its list. The versions kept (snapshots) are left as
    they are: they are read with a single `zone`."""
    op.create_table(
        "template_entity_zones",
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("points", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["template_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_template_entity_zones_entity_id"), "template_entity_zones", ["entity_id"], unique=False)
    op.execute(
        """
        INSERT INTO template_entity_zones (id, entity_id, position, page, points)
        SELECT gen_random_uuid(), id, 0, zone_page, zone_points
        FROM template_entities
        WHERE zone_page IS NOT NULL AND zone_points IS NOT NULL
        """
    )
    op.drop_column("template_entities", "zone_page")
    op.drop_column("template_entities", "zone_points")
    op.add_column("detections", sa.Column("zone_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: only the first zone of an entity is kept."""
    op.drop_column("detections", "zone_index")
    op.add_column("template_entities", sa.Column("zone_points", postgresql.JSONB(), nullable=True))
    op.add_column("template_entities", sa.Column("zone_page", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE template_entities e SET zone_page = z.page, zone_points = z.points
        FROM template_entity_zones z
        WHERE z.entity_id = e.id AND z.position = (
            SELECT min(position) FROM template_entity_zones WHERE entity_id = e.id
        )
        """
    )
    op.drop_index(op.f("ix_template_entity_zones_entity_id"), table_name="template_entity_zones")
    op.drop_table("template_entity_zones")
