from __future__ import annotations

from app.modules.auth.schemas import AuthUser
from app.shared.security import SupabaseJWTClaims


class AuthService:
    def get_auth_user(self, claims: SupabaseJWTClaims) -> AuthUser:
        return AuthUser(
            supabase_user_id=claims.sub,
            email=claims.email,
            role=claims.role,
        )
