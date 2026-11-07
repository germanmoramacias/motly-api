from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.expressions.repository import ExpressionRepository
from app.modules.expressions.schemas import (
    ExpressionCreate,
    ExpressionRead,
    ExpressionUpdate,
)
from app.modules.expressions.service import ExpressionService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.shared.schemas import MessageResponse
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_expression_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
) -> ExpressionService:
    return ExpressionService(ExpressionRepository(session), lessons)


@router.get("", response_model=list[ExpressionRead])
async def list_expressions(
    pagination: PaginationParams = Depends(),
    lesson_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200, description="Case-insensitive text search"),
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> list[ExpressionRead]:
    items = await service.list_for_user(
        user_id=user_id,
        limit=pagination.limit,
        offset=pagination.offset,
        lesson_id=lesson_id,
        q=q,
    )
    return [ExpressionRead.model_validate(item) for item in items]


@router.post("", response_model=ExpressionRead, status_code=status.HTTP_201_CREATED)
async def create_expression(
    payload: ExpressionCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> ExpressionRead:
    item = await service.create_item(user_id=user_id, payload=payload)
    return ExpressionRead.model_validate(item)


@router.patch("/{item_id}", response_model=ExpressionRead)
async def update_expression(
    item_id: UUID,
    payload: ExpressionUpdate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> ExpressionRead:
    item = await service.update_item(item_id=item_id, user_id=user_id, payload=payload)
    return ExpressionRead.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_expression(
    item_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> MessageResponse:
    await service.delete_item(item_id=item_id, user_id=user_id)
    return MessageResponse(message="Expression deleted")
