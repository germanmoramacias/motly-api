from __future__ import annotations

from fastapi import APIRouter

from app.modules.ai.router import router as ai_router
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.expressions.router import router as expressions_router
from app.modules.grammar.router import router as grammar_router
from app.modules.notes.router import router as notes_router
from app.modules.quiz.router import router as quiz_router
from app.modules.users.router import router as users_router
from app.modules.vocabulary.router import router as vocabulary_router

api_v1_router = APIRouter()


@api_v1_router.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users_router, prefix="/users", tags=["users"])
api_v1_router.include_router(notes_router, prefix="/notes", tags=["notes"])
api_v1_router.include_router(vocabulary_router, prefix="/vocabulary", tags=["vocabulary"])
api_v1_router.include_router(grammar_router, prefix="/grammar", tags=["grammar"])
api_v1_router.include_router(expressions_router, prefix="/expressions", tags=["expressions"])
api_v1_router.include_router(quiz_router, prefix="/quiz", tags=["quiz"])
api_v1_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
