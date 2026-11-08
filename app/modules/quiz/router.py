from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.notes.router import get_current_db_user_id
from app.modules.quiz.repository import QuizRepository
from app.modules.quiz.schemas import (
    AnswerCreate,
    LessonOption,
    SessionCreate,
    SessionRead,
    SessionSummary,
)
from app.modules.quiz.service import QuizService, summary
from app.shared.schemas import PaginatedResponse

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[UUID, Depends(get_current_db_user_id)]


def get_quiz_service(session: DbSession) -> QuizService:
    return QuizService(QuizRepository(session))


QuizDependency = Annotated[QuizService, Depends(get_quiz_service)]


@router.get("/sources/lessons", response_model=PaginatedResponse[LessonOption])
async def lesson_options(
    user_id: CurrentUser,
    service: QuizDependency,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    rows, total = await service.repo.lesson_options(user_id, q.strip(), limit, offset)
    return PaginatedResponse[LessonOption](
        items=[LessonOption(id=r.id, title=r.title) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/sessions", response_model=SessionRead, status_code=202)
async def create_session(
    payload: SessionCreate,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    user_id: CurrentUser,
    service: QuizDependency,
):
    return await service.create(user_id, payload, idempotency_key)


@router.get("/sessions/active", response_model=SessionRead | None)
async def active_session(
    user_id: CurrentUser,
    service: QuizDependency,
):
    return await service.active(user_id)


@router.get("/sessions", response_model=PaginatedResponse[SessionSummary])
async def history(
    user_id: CurrentUser,
    service: QuizDependency,
    status: Literal["completed"] = "completed",
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    rows, total = await service.repo.history(user_id, limit, offset)
    return PaginatedResponse[SessionSummary](
        items=[summary(s, answered, correct) for s, answered, correct in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: UUID,
    user_id: CurrentUser,
    service: QuizDependency,
):
    return await service.get(session_id, user_id)


@router.post("/sessions/{session_id}/answers", response_model=SessionRead)
async def answer(
    session_id: UUID,
    payload: AnswerCreate,
    user_id: CurrentUser,
    service: QuizDependency,
):
    return await service.answer(session_id, user_id, payload)


@router.post("/sessions/{session_id}/retry", response_model=SessionRead, status_code=202)
async def retry(
    session_id: UUID,
    user_id: CurrentUser,
    service: QuizDependency,
):
    return await service.retry(session_id, user_id)
