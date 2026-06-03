from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.schemas import AppBaseModel, EntitySchema


class LessonCreate(AppBaseModel):
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)
    source_language: str = Field(default="en", min_length=2, max_length=16)


class LessonUpdate(AppBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content: str | None = Field(default=None, min_length=1)
    source_language: str | None = Field(default=None, min_length=2, max_length=16)


class LessonRead(EntitySchema):
    user_id: UUID
    title: str
    content: str
    source_language: str
