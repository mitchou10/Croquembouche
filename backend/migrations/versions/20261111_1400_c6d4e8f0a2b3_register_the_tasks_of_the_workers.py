"""register the tasks of the workers

Revision ID: c6d4e8f0a2b3
Revises: b5c3d7e9f1a2
Create Date: 2026-11-11 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c6d4e8f0a2b3"
down_revision: str | Sequence[str] | None = "b5c3d7e9f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "worker_heartbeats",
        sa.Column("instance_id", sa.String(length=128), nullable=False),
        sa.Column("service", sa.String(length=64), server_default="", nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("instance_id"),
    )
    op.create_index(op.f("ix_worker_heartbeats_last_seen_at"), "worker_heartbeats", ["last_seen_at"], unique=False)
    op.create_table(
        "worker_tasks",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("author", sa.String(length=200), server_default="", nullable=False),
        sa.Column("instance_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["worker_heartbeats.instance_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", "instance_id"),
    )
    op.create_index(op.f("ix_worker_tasks_name"), "worker_tasks", ["name"], unique=False)
    op.create_index(op.f("ix_worker_tasks_instance_id"), "worker_tasks", ["instance_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_worker_tasks_instance_id"), table_name="worker_tasks")
    op.drop_index(op.f("ix_worker_tasks_name"), table_name="worker_tasks")
    op.drop_table("worker_tasks")
    op.drop_index(op.f("ix_worker_heartbeats_last_seen_at"), table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
