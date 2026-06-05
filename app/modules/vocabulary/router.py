from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.ai.router import get_openai_service
from app.modules.ai.service import OpenAIService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.modules.vocabulary.repository import VocabularyRepository
from app.modules.vocabulary.schemas import VocabularyCreate, VocabularyExtractionResponse, VocabularyRead
from app.modules.vocabulary.service import VocabularyService
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_vocabulary_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
    ai: OpenAIService = Depends(get_openai_service),
) -> VocabularyService:
    return VocabularyService(VocabularyRepository(session), lessons, ai)


@router.get("", response_model=list[VocabularyRead])
async def list_vocabulary(
    pagination: PaginationParams = Depends(),
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> list[VocabularyRead]:
    items = await service.list_for_user(user_id=user_id, limit=pagination.limit, offset=pagination.offset)
    return [VocabularyRead.model_validate(item) for item in items]


@router.post("", response_model=VocabularyRead, status_code=status.HTTP_201_CREATED)
async def create_vocabulary_item(
    payload: VocabularyCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> VocabularyRead:
    item = await service.create_item(user_id=user_id, payload=payload)
    return VocabularyRead.model_validate(item)


@router.get("/lessons/{lesson_id}", response_model=list[VocabularyRead])
async def list_lesson_vocabulary(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> list[VocabularyRead]:
    items = await service.list_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return [VocabularyRead.model_validate(item) for item in items]


@router.post(
    "/lessons/{lesson_id}/extract",
    response_model=VocabularyExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extract_lesson_vocabulary(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> VocabularyExtractionResponse:
    items = await service.extract_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return VocabularyExtractionResponse(items=[VocabularyRead.model_validate(item) for item in items])
