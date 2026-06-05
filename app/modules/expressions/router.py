from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.ai.router import get_openai_service
from app.modules.ai.service import OpenAIService
from app.modules.expressions.repository import ExpressionRepository
from app.modules.expressions.schemas import ExpressionCreate, ExpressionExtractionResponse, ExpressionRead
from app.modules.expressions.service import ExpressionService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_expression_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
    ai: OpenAIService = Depends(get_openai_service),
) -> ExpressionService:
    return ExpressionService(ExpressionRepository(session), lessons, ai)


@router.get("", response_model=list[ExpressionRead])
async def list_expressions(
    pagination: PaginationParams = Depends(),
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> list[ExpressionRead]:
    items = await service.list_for_user(user_id=user_id, limit=pagination.limit, offset=pagination.offset)
    return [ExpressionRead.model_validate(item) for item in items]


@router.post("", response_model=ExpressionRead, status_code=status.HTTP_201_CREATED)
async def create_expression(
    payload: ExpressionCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> ExpressionRead:
    item = await service.create_item(user_id=user_id, payload=payload)
    return ExpressionRead.model_validate(item)


@router.get("/lessons/{lesson_id}", response_model=list[ExpressionRead])
async def list_lesson_expressions(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> list[ExpressionRead]:
    items = await service.list_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return [ExpressionRead.model_validate(item) for item in items]


@router.post(
    "/lessons/{lesson_id}/extract",
    response_model=ExpressionExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extract_lesson_expressions(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: ExpressionService = Depends(get_expression_service),
) -> ExpressionExtractionResponse:
    items = await service.extract_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return ExpressionExtractionResponse(items=[ExpressionRead.model_validate(item) for item in items])
