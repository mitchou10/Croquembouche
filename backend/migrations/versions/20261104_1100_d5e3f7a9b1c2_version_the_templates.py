"""version the templates

Revision ID: d5e3f7a9b1c2
Revises: c4d2e6f8a0b1
Create Date: 2026-11-04 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e3f7a9b1c2"
down_revision: str | Sequence[str] | None = "c4d2e6f8a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The snapshot of a model as the application writes it (see `_template_fields_dict`).
SNAPSHOT = """
jsonb_build_object(
    'name', t.name,
    'description', t.description,
    'categories', COALESCE((
        SELECT jsonb_agg(c.name ORDER BY c.name)
        FROM template_categories tc JOIN categories c ON c.id = tc.category_id
        WHERE tc.template_id = t.id), '[]'::jsonb),
    'entities', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'id', e.id::text, 'name', e.name, 'definition', e.definition, 'type', e.type, 'examples', e.examples,
            'zone', CASE WHEN e.zone_page IS NULL THEN NULL
                         ELSE jsonb_build_object('page', e.zone_page, 'points', e.zone_points) END)
            ORDER BY e.position)
        FROM template_entities e WHERE e.template_id = t.id), '[]'::jsonb),
    'pages', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'page', p.page, 'name', COALESCE(p.name, ''), 'description', COALESCE(p.description, ''))
            ORDER BY p.page)
        FROM template_pages p
        WHERE p.template_id = t.id AND (COALESCE(p.name, '') <> '' OR COALESCE(p.description, '') <> '')),
        '[]'::jsonb)
)
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("templates", sa.Column("major", sa.Integer(), server_default="1", nullable=False))
    op.add_column("templates", sa.Column("minor", sa.Integer(), server_default="0", nullable=False))
    op.add_column("templates", sa.Column("patch", sa.Integer(), server_default="0", nullable=False))
    op.create_table(
        "template_versions",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("major", sa.Integer(), nullable=False),
        sa.Column("minor", sa.Integer(), nullable=False),
        sa.Column("patch", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["user_profiles.user_id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "major", "minor", "patch"),
    )
    op.create_index(op.f("ix_template_versions_template_id"), "template_versions", ["template_id"], unique=False)
    op.create_index(op.f("ix_template_versions_document_id"), "template_versions", ["document_id"], unique=False)
    # The models there already are start at 1.0.0, with their snapshot.
    op.execute(
        f"""
        INSERT INTO template_versions (id, template_id, major, minor, patch, snapshot, document_id, author_id, created_at)
        SELECT gen_random_uuid(), t.id, 1, 0, 0, {SNAPSHOT}, t.document_id, t.owner_id, t.created_at
        FROM templates t
        """
    )
    op.add_column(
        "runs",
        sa.Column("template_versions", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("runs", "template_versions")
    op.drop_index(op.f("ix_template_versions_document_id"), table_name="template_versions")
    op.drop_index(op.f("ix_template_versions_template_id"), table_name="template_versions")
    op.drop_table("template_versions")
    op.drop_column("templates", "patch")
    op.drop_column("templates", "minor")
    op.drop_column("templates", "major")
