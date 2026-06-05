from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class GrammarTopicCreate(AppBaseModel):
    lesson_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1)
    examples: list[str] = Field(default_factory=list)


class GrammarTopicRead(EntitySchema):
    user_id: UUID
    lesson_id: UUID | None
    name: str
    explanation: str
    examples: list[str]


class GrammarExtractionResponse(AppBaseModel):
    items: list[GrammarTopicRead]
