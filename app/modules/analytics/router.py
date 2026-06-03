from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import LearningStats, QuizResultCreate, QuizResultRead
from app.modules.analytics.service import AnalyticsService
from app.modules.notes.router import get_current_db_user_id
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_analytics_service(session: AsyncSession = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(session))


@router.get("/stats", response_model=LearningStats)
async def get_learning_stats(
    user_id: UUID = Depends(get_current_db_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> LearningStats:
    return await service.get_learning_stats(user_id)


@router.post("/quiz-results", response_model=QuizResultRead, status_code=status.HTTP_201_CREATED)
async def create_quiz_result(
    payload: QuizResultCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> QuizResultRead:
    result = await service.create_quiz_result(user_id=user_id, payload=payload)
    return QuizResultRead.model_validate(result)


@router.get("/quiz-results", response_model=list[QuizResultRead])
async def list_quiz_results(
    pagination: PaginationParams = Depends(),
    user_id: UUID = Depends(get_current_db_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[QuizResultRead]:
    results = await service.list_quiz_results(
        user_id=user_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [QuizResultRead.model_validate(result) for result in results]
