from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PENDING_STATUSES = ("generating", "in_progress", "generation_failed")


class QuizSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        Index(
            "uq_quiz_sessions_pending_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('generating', 'in_progress', 'generation_failed')"),
        ),
        Index("ix_quiz_sessions_history", "user_id", "status", "completed_at", "id"),
        CheckConstraint(
            "status IN ('generating', 'in_progress', 'completed', 'generation_failed')",
            name="status",
        ),
        CheckConstraint("scope IN ('all', 'lesson')", name="scope"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL")
    )
    scope: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(24), default="generating")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    context_snapshot: Mapped[list[dict]] = mapped_column(JSON)
    english_level: Mapped[str | None] = mapped_column(String(32))
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_version: Mapped[str] = mapped_column(String(32), default="quiz-v1")
    model: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(40))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuizQuestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("session_id", "position"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(24))
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[dict]] = mapped_column(JSON)
    correct_option_id: Mapped[str] = mapped_column(String(36))
    explanation: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSON)


class QuizAnswer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quiz_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), unique=True
    )
    selected_option_id: Mapped[str] = mapped_column(String(36))
    is_correct: Mapped[bool]
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QuizGenerationJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quiz_generation_jobs"
    __table_args__ = (Index("ix_quiz_jobs_ready", "status", "available_at"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
