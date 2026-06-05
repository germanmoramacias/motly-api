from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import cast

import httpx
import jwt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import UnauthorizedError


class SupabaseJWTClaims(BaseModel):
    sub: str
    aud: str | list[str]
    email: str | None = None
    role: str | None = None
    exp: int
    iss: str | None = None
    user_metadata: dict[str, object] = Field(default_factory=dict)


@dataclass
class JwksCache:
    jwks: dict[str, object] | None = None
    expires_at: float = 0


_jwks_cache = JwksCache()


async def _load_jwks() -> dict[str, object]:
    if settings.supabase_jwks_url is None:
        raise UnauthorizedError("Supabase JWKS URL is not configured")

    now = monotonic()
    if _jwks_cache.jwks is not None and _jwks_cache.expires_at > now:
        return _jwks_cache.jwks

    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(str(settings.supabase_jwks_url))
        response.raise_for_status()
        jwks = cast(dict[str, object], response.json())

    _jwks_cache.jwks = jwks
    _jwks_cache.expires_at = now + 300
    return jwks


async def verify_supabase_jwt(token: str) -> SupabaseJWTClaims:
    jwks = await _load_jwks()

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid token header") from exc

    algorithm = header.get("alg")
    if algorithm not in {"RS256", "ES256"}:
        raise UnauthorizedError(f"Unsupported token algorithm: {algorithm}")

    key_id = header.get("kid")
    keys = cast(list[dict[str, object]], jwks.get("keys", []))
    jwk_data = next((key for key in keys if key.get("kid") == key_id), None)
    if jwk_data is None:
        raise UnauthorizedError("Invalid token signing key")

    try:
        signing_key = jwt.PyJWK.from_dict(jwk_data).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
            options={"verify_iss": settings.supabase_jwt_issuer is not None},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    return SupabaseJWTClaims.model_validate(payload)
