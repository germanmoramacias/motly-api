from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.shared.schemas import AppBaseModel

CreatedAtSort = Literal["created_at_desc", "created_at_asc"]
VocabularySort = CreatedAtSort | Literal["term_asc", "term_desc"]
ExpressionSort = CreatedAtSort | Literal["text_asc", "text_desc"]


class PaginationParams(AppBaseModel):
    limit: int = Field(default=1000, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)
