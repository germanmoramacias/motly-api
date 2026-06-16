from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class GrammarTopicCreate(AppBaseModel):
    lesson_id: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)
    source_language: str = Field(default="en", min_length=2, max_length=16)


class GrammarTopicUpdate(AppBaseModel):
    lesson_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content: str | None = Field(default=None, min_length=1)
    source_language: str | None = Field(default=None, min_length=2, max_length=16)


class GrammarTopicRead(EntitySchema):
    user_id: UUID
    lesson_id: UUID | None
    title: str
    content: str
    source_language: str
