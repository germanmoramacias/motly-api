"""user owned learning items

Revision ID: 20260605_0002
Revises: 20260529_0001
Create Date: 2026-06-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260605_0002"
down_revision: str | None = "20260529_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("vocabulary", "expressions", "grammar_topics"):
        op.add_column(table_name, sa.Column("user_id", sa.Uuid(), nullable=True))

        op.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET user_id = lessons.user_id
                FROM lessons
                WHERE {table_name}.lesson_id = lessons.id
                """
            )
        )

        op.alter_column(table_name, "user_id", existing_type=sa.Uuid(), nullable=False)
        op.create_index(f"ix_{table_name}_user_id", table_name, ["user_id"])
        op.create_foreign_key(
            f"fk_{table_name}_user_id_users",
            table_name,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

        _drop_foreign_key(table_name=table_name, column_name="lesson_id")
        op.alter_column(table_name, "lesson_id", existing_type=sa.Uuid(), nullable=True)
        op.create_foreign_key(
            f"fk_{table_name}_lesson_id_lessons",
            table_name,
            "lessons",
            ["lesson_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table_name in ("vocabulary", "expressions", "grammar_topics"):
        op.execute(sa.text(f"DELETE FROM {table_name} WHERE lesson_id IS NULL"))
        op.drop_constraint(f"fk_{table_name}_lesson_id_lessons", table_name, type_="foreignkey")
        op.alter_column(table_name, "lesson_id", existing_type=sa.Uuid(), nullable=False)
        op.create_foreign_key(
            f"fk_{table_name}_lesson_id_lessons",
            table_name,
            "lessons",
            ["lesson_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.drop_constraint(f"fk_{table_name}_user_id_users", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_user_id", table_name=table_name)
        op.drop_column(table_name, "user_id")


def _drop_foreign_key(table_name: str, column_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE constraint_name text;
            BEGIN
                SELECT con.conname INTO constraint_name
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
                WHERE con.contype = 'f'
                  AND rel.relname = '{table_name}'
                  AND att.attname = '{column_name}'
                LIMIT 1;

                IF constraint_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table_name}', constraint_name);
                END IF;
            END $$;
            """
        )
    )
