from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class QuizResultCreate(AppBaseModel):
    lesson_id: UUID | None = None
    score: int = Field(ge=0)
    total_questions: int = Field(gt=0)
    result_metadata: dict[str, object] = Field(default_factory=dict)


class QuizResultRead(EntitySchema):
    quiz_session_id: UUID | None
    correct_count: int | None
    score_percent: float | None
    user_id: UUID
    lesson_id: UUID | None
    score: int
    total_questions: int
    result_metadata: dict[str, object]


class LearningStats(AppBaseModel):
    lessons_count: int
    vocabulary_count: int
    expressions_count: int
    grammar_topics_count: int
    writing_submissions_count: int
    quiz_attempts_count: int
    average_quiz_score: float | None
