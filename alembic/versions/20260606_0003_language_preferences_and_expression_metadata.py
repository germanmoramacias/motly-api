"""language preferences and expression metadata

Revision ID: 20260606_0003
Revises: 20260605_0002
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260606_0003"
down_revision: str | None = "20260605_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("vocabulary", "difficulty")

    op.add_column("expressions", sa.Column("keyword", sa.String(length=120), nullable=True))
    op.add_column("expressions", sa.Column("group", sa.String(length=80), nullable=True))

    op.add_column(
        "users",
        sa.Column("source_languages", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "users",
        sa.Column("target_languages", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("users", "target_languages")
    op.drop_column("users", "source_languages")

    op.drop_column("expressions", "group")
    op.drop_column("expressions", "keyword")

    op.add_column("vocabulary", sa.Column("difficulty", sa.String(length=32), nullable=True))
