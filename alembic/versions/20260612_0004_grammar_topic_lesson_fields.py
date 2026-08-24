"""grammar topic lesson fields

Revision ID: 20260612_0004
Revises: 20260606_0003
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0004"
down_revision: str | None = "20260606_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "grammar_topics",
        "name",
        new_column_name="title",
        existing_type=sa.String(length=160),
        existing_nullable=False,
    )
    op.alter_column(
        "grammar_topics",
        "title",
        type_=sa.String(length=180),
        existing_type=sa.String(length=160),
        existing_nullable=False,
    )
    op.alter_column(
        "grammar_topics",
        "explanation",
        new_column_name="content",
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.add_column(
        "grammar_topics",
        sa.Column("source_language", sa.String(length=16), nullable=False, server_default="en"),
    )
    op.drop_column("grammar_topics", "examples")


def downgrade() -> None:
    op.add_column(
        "grammar_topics",
        sa.Column("examples", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.drop_column("grammar_topics", "source_language")
    op.alter_column(
        "grammar_topics",
        "content",
        new_column_name="explanation",
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "grammar_topics",
        "title",
        type_=sa.String(length=160),
        existing_type=sa.String(length=180),
        existing_nullable=False,
    )
    op.alter_column(
        "grammar_topics",
        "title",
        new_column_name="name",
        existing_type=sa.String(length=160),
        existing_nullable=False,
    )
