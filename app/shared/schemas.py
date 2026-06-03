from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EntitySchema(AppBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class MessageResponse(AppBaseModel):
    message: str
