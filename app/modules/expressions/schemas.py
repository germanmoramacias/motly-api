from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class ExpressionCreate(AppBaseModel):
    lesson_id: UUID | None = None
    text: str = Field(min_length=1, max_length=180)
    keyword: str | None = Field(default=None, max_length=120)
    group: str | None = Field(default=None, max_length=80)
    meaning: str = Field(min_length=1)
    example: str | None = None


class ExpressionUpdate(AppBaseModel):
    lesson_id: UUID | None = None
    text: str | None = Field(default=None, min_length=1, max_length=180)
    keyword: str | None = Field(default=None, max_length=120)
    group: str | None = Field(default=None, max_length=80)
    meaning: str | None = Field(default=None, min_length=1)
    example: str | None = None


class ExpressionRead(EntitySchema):
    user_id: UUID
    lesson_id: UUID | None
    text: str
    keyword: str | None
    group: str | None
    meaning: str
    example: str | None
