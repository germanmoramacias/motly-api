from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.errors import UnauthorizedError
from app.modules.auth.schemas import AuthUser
from app.modules.auth.service import AuthService
from app.shared.security import SupabaseJWTClaims

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


def get_current_claims(request: Request) -> SupabaseJWTClaims:
    claims = request.state.user
    if claims is None:
        raise UnauthorizedError()
    return claims


@router.get("/me", response_model=AuthUser)
async def read_current_auth_user(
    claims: SupabaseJWTClaims = Depends(get_current_claims),
    service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    return service.get_auth_user(claims)
