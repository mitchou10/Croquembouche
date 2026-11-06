"""the image and table types, and tags on an entity

Revision ID: a8b6c0d2e4f5
Revises: f7a5b9c1d3e4
Create Date: 2026-11-06 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8b6c0d2e4f5"
down_revision: str | Sequence[str] | None = "f7a5b9c1d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TYPES = [
    (
        "image",
        "Image",
        "Une image sans texte à lire : une signature, un tampon, un logo, une photo. La zone en est recadrée et gardée telle quelle.",
    ),
    (
        "table",
        "Tableau",
        "Des lignes et des colonnes de valeurs (lignes d’une facture, d’une commande…). La zone entoure tout le tableau.",
    ),
]

entity_types = sa.table(
    "entity_types", sa.column("value", sa.String), sa.column("label", sa.String), sa.column("definition", sa.Text)
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(entity_types, [{"value": v, "label": label, "definition": d} for v, label, d in NEW_TYPES])
    # Optional details on an entity, free words like its examples: what the entities already there have is none.
    op.add_column(
        "template_entities",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("template_entities", "tags")
    # An entity of one of these types cannot be left without its type: they go back to text.
    op.execute(sa.text("UPDATE template_entities SET type = 'text' WHERE type IN ('image', 'table')"))
    op.execute(entity_types.delete().where(entity_types.c.value.in_([v for v, _, _ in NEW_TYPES])))
