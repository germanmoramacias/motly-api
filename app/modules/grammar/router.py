from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.grammar.repository import GrammarRepository
from app.modules.grammar.schemas import GrammarTopicCreate, GrammarTopicRead, GrammarTopicUpdate
from app.modules.grammar.service import GrammarService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.shared.schemas import MessageResponse
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_grammar_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
) -> GrammarService:
    return GrammarService(GrammarRepository(session), lessons)


@router.get("", response_model=list[GrammarTopicRead])
async def list_grammar_topics(
    pagination: PaginationParams = Depends(),
    lesson_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> list[GrammarTopicRead]:
    items = await service.list_for_user(
        user_id=user_id,
        limit=pagination.limit,
        offset=pagination.offset,
        lesson_id=lesson_id,
    )
    return [GrammarTopicRead.model_validate(item) for item in items]


@router.post("", response_model=GrammarTopicRead, status_code=status.HTTP_201_CREATED)
async def create_grammar_topic(
    payload: GrammarTopicCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> GrammarTopicRead:
    item = await service.create_topic(user_id=user_id, payload=payload)
    return GrammarTopicRead.model_validate(item)


@router.patch("/{item_id}", response_model=GrammarTopicRead)
async def update_grammar_topic(
    item_id: UUID,
    payload: GrammarTopicUpdate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> GrammarTopicRead:
    item = await service.update_topic(item_id=item_id, user_id=user_id, payload=payload)
    return GrammarTopicRead.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_grammar_topic(
    item_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> MessageResponse:
    await service.delete_topic(item_id=item_id, user_id=user_id)
    return MessageResponse(message="Grammar topic deleted")
