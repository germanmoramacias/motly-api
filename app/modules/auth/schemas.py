from __future__ import annotations

from app.shared.schemas import AppBaseModel


class AuthSession(AppBaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUser(AppBaseModel):
    supabase_user_id: str
    email: str | None = None
    role: str | None = None
