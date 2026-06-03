from __future__ import annotations

from pydantic import EmailStr, Field

from app.shared.schemas import AppBaseModel, EntitySchema


class UserCreate(AppBaseModel):
    supabase_user_id: str = Field(min_length=1, max_length=128)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=160)
    english_level: str | None = Field(default=None, max_length=32)


class UserUpdate(AppBaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    english_level: str | None = Field(default=None, max_length=32)


class UserRead(EntitySchema):
    supabase_user_id: str
    email: EmailStr
    full_name: str | None
    english_level: str | None
    is_active: bool
