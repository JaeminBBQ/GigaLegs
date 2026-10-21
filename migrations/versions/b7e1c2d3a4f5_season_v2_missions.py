"""season v2: missions table, rides.sport

Revision ID: b7e1c2d3a4f5
Revises: fc9233cbf784
Create Date: 2026-10-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e1c2d3a4f5"
down_revision: str | Sequence[str] | None = "fc9233cbf784"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("plan_week", sa.Integer(), nullable=False),
        sa.Column("slot_key", sa.String(length=20), nullable=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("level", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("hard", sa.Boolean(), nullable=False),
        sa.Column("long", sa.Boolean(), nullable=False),
        sa.Column("tempo", sa.Boolean(), nullable=False),
        sa.Column("ref", sa.String(length=40), nullable=False),
        sa.Column("pain", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("missions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_missions_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_missions_date"), ["date"], unique=False)
    with op.batch_alter_table("rides", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("sport", sa.String(length=8), nullable=False, server_default="ride")
        )


def downgrade() -> None:
    with op.batch_alter_table("rides", schema=None) as batch_op:
        batch_op.drop_column("sport")
    with op.batch_alter_table("missions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_missions_date"))
        batch_op.drop_index(batch_op.f("ix_missions_user_id"))
    op.drop_table("missions")
