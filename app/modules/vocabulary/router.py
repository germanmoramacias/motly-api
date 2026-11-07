from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.modules.vocabulary.repository import VocabularyRepository
from app.modules.vocabulary.schemas import (
    VocabularyCreate,
    VocabularyRead,
    VocabularyUpdate,
)
from app.modules.vocabulary.service import VocabularyService
from app.shared.schemas import MessageResponse
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_vocabulary_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
) -> VocabularyService:
    return VocabularyService(VocabularyRepository(session), lessons)


@router.get("", response_model=list[VocabularyRead])
async def list_vocabulary(
    pagination: PaginationParams = Depends(),
    lesson_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200, description="Case-insensitive text search"),
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> list[VocabularyRead]:
    items = await service.list_for_user(
        user_id=user_id,
        limit=pagination.limit,
        offset=pagination.offset,
        lesson_id=lesson_id,
        q=q,
    )
    return [VocabularyRead.model_validate(item) for item in items]


@router.post("", response_model=VocabularyRead, status_code=status.HTTP_201_CREATED)
async def create_vocabulary_item(
    payload: VocabularyCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> VocabularyRead:
    item = await service.create_item(user_id=user_id, payload=payload)
    return VocabularyRead.model_validate(item)


@router.patch("/{item_id}", response_model=VocabularyRead)
async def update_vocabulary_item(
    item_id: UUID,
    payload: VocabularyUpdate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> VocabularyRead:
    item = await service.update_item(item_id=item_id, user_id=user_id, payload=payload)
    return VocabularyRead.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_vocabulary_item(
    item_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: VocabularyService = Depends(get_vocabulary_service),
) -> MessageResponse:
    await service.delete_item(item_id=item_id, user_id=user_id)
    return MessageResponse(message="Vocabulary item deleted")
