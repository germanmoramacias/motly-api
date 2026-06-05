from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class ExpressionCreate(AppBaseModel):
    lesson_id: UUID | None = None
    text: str = Field(min_length=1, max_length=180)
    meaning: str = Field(min_length=1)
    example: str | None = None


class ExpressionRead(EntitySchema):
    user_id: UUID
    lesson_id: UUID | None
    text: str
    meaning: str
    example: str | None


class ExpressionExtractionResponse(AppBaseModel):
    items: list[ExpressionRead]
