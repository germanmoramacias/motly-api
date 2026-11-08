from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.schemas import AppBaseModel


class SessionCreate(AppBaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scope: Literal["all", "lesson"]
    lesson_id: UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        if (self.scope == "lesson") != (self.lesson_id is not None):
            raise ValueError("lesson_id is required only for lesson scope")
        return self


class AnswerCreate(AppBaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: UUID
    selected_option_id: UUID


class OptionRead(AppBaseModel):
    id: str
    text: str


class SourceRead(AppBaseModel):
    id: str
    kind: str
    title: str


class QuestionRead(AppBaseModel):
    id: UUID
    position: int
    category: str
    question: str
    options: list[OptionRead]


class AnswerRead(AppBaseModel):
    question: QuestionRead
    selected_option_id: str
    correct_option_id: str
    is_correct: bool
    explanation: str
    sources: list[SourceRead]
    submitted_at: datetime


class SessionSummary(AppBaseModel):
    id: UUID
    title: str
    scope: Literal["all", "lesson"]
    lesson_id: UUID | None
    status: Literal["generating", "in_progress", "completed", "generation_failed"]
    question_count: int
    answered_count: int
    correct_count: int
    score_percent: float | None
    created_at: datetime
    completed_at: datetime | None
    error_code: str | None


class SessionRead(SessionSummary):
    current_question: QuestionRead | None
    answers: list[AnswerRead]


class LessonOption(AppBaseModel):
    id: UUID
    title: str


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Literal["vocabulary", "grammar", "expression"]
    question: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(min_length=2, max_length=5)
    correct_index: int = Field(ge=0, le=4)
    explanation: str = Field(min_length=1, max_length=3000)
    source_ids: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        normalized = [option.strip().casefold() for option in self.options]
        if not all(normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("Options must be nonempty and distinct")
        if self.correct_index >= len(self.options):
            raise ValueError("Correct option must exist")
        return self


class GeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        prompts = [" ".join(q.question.casefold().split()) for q in self.questions]
        if len(prompts) != len(set(prompts)):
            raise ValueError("Duplicate questions")
        return self
