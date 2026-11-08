from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EntitySchema(AppBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class MessageResponse(AppBaseModel):
    message: str


class PaginatedResponse[T](AppBaseModel):
    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    @computed_field
    @property
    def total_pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit
