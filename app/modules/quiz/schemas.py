from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.modules.ai.schemas import QuizQuestion
from app.shared.schemas import AppBaseModel


class QuizGenerateRequest(AppBaseModel):
    lesson_id: UUID
    total_questions: int = Field(default=5, ge=1, le=20)


class QuizGenerateResponse(AppBaseModel):
    questions: list[QuizQuestion]
