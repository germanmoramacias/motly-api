from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.ai.router import get_openai_service
from app.modules.ai.service import OpenAIService
from app.modules.grammar.repository import GrammarRepository
from app.modules.grammar.schemas import GrammarExtractionResponse, GrammarTopicRead
from app.modules.grammar.service import GrammarService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService

router = APIRouter()


def get_grammar_service(
    session: AsyncSession = Depends(get_db_session),
    lessons: LessonService = Depends(get_lesson_service),
    ai: OpenAIService = Depends(get_openai_service),
) -> GrammarService:
    return GrammarService(GrammarRepository(session), lessons, ai)


@router.get("/lessons/{lesson_id}", response_model=list[GrammarTopicRead])
async def list_lesson_grammar(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> list[GrammarTopicRead]:
    items = await service.list_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return [GrammarTopicRead.model_validate(item) for item in items]


@router.post(
    "/lessons/{lesson_id}/extract",
    response_model=GrammarExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extract_lesson_grammar(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: GrammarService = Depends(get_grammar_service),
) -> GrammarExtractionResponse:
    items = await service.extract_for_lesson(lesson_id=lesson_id, user_id=user_id)
    return GrammarExtractionResponse(items=[GrammarTopicRead.model_validate(item) for item in items])
