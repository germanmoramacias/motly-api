from __future__ import annotations

from uuid import UUID

from app.core.errors import NotFoundError
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate
from app.shared.security import SupabaseJWTClaims


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_user(self, user_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def get_or_create_from_claims(self, claims: SupabaseJWTClaims) -> User:
        user = await self.repository.get_by_supabase_id(claims.sub)
        if user is not None:
            return user

        email = claims.email or f"{claims.sub}@supabase.local"
        full_name = claims.user_metadata.get("full_name")
        payload = UserCreate(
            supabase_user_id=claims.sub,
            email=email,
            full_name=full_name if isinstance(full_name, str) else None,
        )
        return await self.repository.create(payload)

    async def update_user(self, user_id: UUID, payload: UserUpdate) -> User:
        user = await self.get_user(user_id)
        return await self.repository.update(user, payload)
