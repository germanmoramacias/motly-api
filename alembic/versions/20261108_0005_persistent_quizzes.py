"""Persistent quiz sessions and durable generation jobs.

Revision ID: 20261108_0005
Revises: 20260612_0004
"""

from hashlib import sha256

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision = "20261108_0005"
down_revision = "20260612_0004"
branch_labels = None
depends_on = None


def identity():
    return sa.Column("id", sa.Uuid(), primary_key=True, nullable=False)


def session_fk():
    return sa.Column(
        "session_id",
        sa.Uuid(),
        sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )


def _create_tables():
    op.create_table(
        "quiz_sessions",
        identity(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("lesson_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="SET NULL")),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("english_level", sa.String(32)),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("model", sa.String(100)),
        sa.Column("error_code", sa.String(40)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "idempotency_key"),
        sa.CheckConstraint(
            "status IN ('generating', 'in_progress', 'completed', 'generation_failed')",
            name="status",
        ),
        sa.CheckConstraint("scope IN ('all', 'lesson')", name="scope"),
    )
    op.create_index(
        "uq_quiz_sessions_pending_user",
        "quiz_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('generating', 'in_progress', 'generation_failed')"),
    )
    op.create_index(
        "ix_quiz_sessions_history", "quiz_sessions", ["user_id", "status", "completed_at", "id"]
    )
    op.create_table(
        "quiz_questions",
        identity(),
        session_fk(),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_option_id", sa.String(36), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.UniqueConstraint("session_id", "position"),
    )
    op.create_index("ix_quiz_questions_session_id", "quiz_questions", ["session_id"])
    op.create_table(
        "quiz_answers",
        identity(),
        sa.Column(
            "question_id",
            sa.Uuid(),
            sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("selected_option_id", sa.String(36), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "quiz_generation_jobs",
        identity(),
        session_fk(),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True)),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_quiz_jobs_ready", "quiz_generation_jobs", ["status", "available_at"])


def _schemas():
    bind = op.get_bind()
    schema = (
        "public" if context.is_offline_mode() else bind.scalar(sa.text("SELECT current_schema()"))
    )
    archive = schema + "_quiz_0005_archive"
    if len(archive) > 63:
        archive = schema[:32] + "_quiz0005_" + sha256(schema.encode()).hexdigest()[:12]
    quote = bind.dialect.identifier_preparer.quote_identifier
    return schema, archive, quote(schema), quote(archive)


def upgrade():
    _, archive, target_sql, archive_sql = _schemas()
    restoring = not context.is_offline_mode() and sa.inspect(op.get_bind()).has_table(
        "quiz_sessions", schema=archive
    )
    if restoring:
        for table in ("quiz_sessions", "quiz_questions", "quiz_answers", "quiz_generation_jobs"):
            op.execute(f'ALTER TABLE {archive_sql}."{table}" SET SCHEMA {target_sql}')
    else:
        _create_tables()
    op.add_column("quiz_results", sa.Column("quiz_session_id", sa.Uuid()))
    op.add_column("quiz_results", sa.Column("correct_count", sa.Integer()))
    op.add_column("quiz_results", sa.Column("score_percent", sa.Float()))
    op.create_foreign_key(
        "fk_quiz_results_quiz_session_id_quiz_sessions",
        "quiz_results",
        "quiz_sessions",
        ["quiz_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_quiz_results_quiz_session_id", "quiz_results", ["quiz_session_id"]
    )
    # These tables are only accessed via the authenticated FastAPI backend / worker.
    # On Supabase, no direct anon/authenticated Data API access, including answer keys.
    for table in ("quiz_sessions", "quiz_questions", "quiz_answers", "quiz_generation_jobs"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')

    if restoring:
        op.execute(f"""UPDATE {target_sql}.quiz_results AS result
            SET quiz_session_id = saved.quiz_session_id,
                correct_count = saved.correct_count,
                score_percent = saved.score_percent
            FROM {archive_sql}.quiz_result_links AS saved
            WHERE result.id = saved.id""")
        op.execute(f"DROP TABLE {archive_sql}.quiz_result_links")
        op.execute(f"DROP SCHEMA {archive_sql}")


def downgrade():
    # Keep all quiz data recoverable. A later upgrade restores the same sessions.
    _, _, target_sql, archive_sql = _schemas()
    op.execute(f"CREATE SCHEMA {archive_sql}")
    op.execute(f"REVOKE ALL ON SCHEMA {archive_sql} FROM PUBLIC")
    op.execute(f"""CREATE TABLE {archive_sql}.quiz_result_links AS
        SELECT id, quiz_session_id, correct_count, score_percent
        FROM {target_sql}.quiz_results WHERE quiz_session_id IS NOT NULL""")
    op.drop_constraint("uq_quiz_results_quiz_session_id", "quiz_results", type_="unique")
    op.drop_constraint(
        "fk_quiz_results_quiz_session_id_quiz_sessions", "quiz_results", type_="foreignkey"
    )
    for column in ("score_percent", "correct_count", "quiz_session_id"):
        op.drop_column("quiz_results", column)
    for table in ("quiz_sessions", "quiz_questions", "quiz_answers", "quiz_generation_jobs"):
        op.execute(f'ALTER TABLE {target_sql}."{table}" SET SCHEMA {archive_sql}')
