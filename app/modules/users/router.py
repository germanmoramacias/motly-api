from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.router import get_current_claims
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserRead, UserUpdate
from app.modules.users.service import UserService
from app.shared.security import SupabaseJWTClaims

router = APIRouter()


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(UserRepository(session))


@router.get("/me", response_model=UserRead)
async def read_current_user(
    claims: SupabaseJWTClaims = Depends(get_current_claims),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.get_or_create_from_claims(claims)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.update_user(user_id, payload)
    return UserRead.model_validate(user)
