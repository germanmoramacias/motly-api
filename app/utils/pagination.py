from __future__ import annotations

from pydantic import Field

from app.shared.schemas import AppBaseModel


class PaginationParams(AppBaseModel):
    limit: int = Field(default=1000, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)
