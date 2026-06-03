from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.shared.security import verify_supabase_jwt

PUBLIC_PATH_SUFFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user = None

        if request.method == "OPTIONS" or request.url.path.endswith(PUBLIC_PATH_SUFFIXES):
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            request.state.user = await verify_supabase_jwt(token)

        return await call_next(request)
