from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class VocabularyCreate(AppBaseModel):
    lesson_id: UUID | None = None
    term: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=1)
    example: str | None = None


class VocabularyRead(EntitySchema):
    user_id: UUID
    lesson_id: UUID | None
    term: str
    definition: str
    example: str | None


class VocabularyExtractionRequest(AppBaseModel):
    lesson_id: UUID


class VocabularyExtractionResponse(AppBaseModel):
    items: list[VocabularyRead]
