from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class VocabularyCreate(AppBaseModel):
    term: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=1)
    example: str | None = None
    difficulty: str | None = Field(default=None, max_length=32)


class VocabularyRead(EntitySchema):
    lesson_id: UUID
    term: str
    definition: str
    example: str | None
    difficulty: str | None


class VocabularyExtractionRequest(AppBaseModel):
    lesson_id: UUID


class VocabularyExtractionResponse(AppBaseModel):
    items: list[VocabularyRead]
