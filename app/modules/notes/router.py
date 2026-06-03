from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.router import get_current_claims
from app.modules.notes.repository import LessonRepository
from app.modules.notes.schemas import LessonCreate, LessonRead, LessonUpdate
from app.modules.notes.service import LessonService
from app.modules.users.router import get_user_service
from app.modules.users.service import UserService
from app.shared.schemas import MessageResponse
from app.shared.security import SupabaseJWTClaims
from app.utils.pagination import PaginationParams

router = APIRouter()


def get_lesson_service(session: AsyncSession = Depends(get_db_session)) -> LessonService:
    return LessonService(LessonRepository(session))


async def get_current_db_user_id(
    claims: SupabaseJWTClaims = Depends(get_current_claims),
    users: UserService = Depends(get_user_service),
) -> UUID:
    user = await users.get_or_create_from_claims(claims)
    return user.id


@router.get("", response_model=list[LessonRead])
async def list_lessons(
    pagination: PaginationParams = Depends(),
    user_id: UUID = Depends(get_current_db_user_id),
    service: LessonService = Depends(get_lesson_service),
) -> list[LessonRead]:
    lessons = await service.list_lessons(user_id=user_id, limit=pagination.limit, offset=pagination.offset)
    return [LessonRead.model_validate(lesson) for lesson in lessons]


@router.post("", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: LessonService = Depends(get_lesson_service),
) -> LessonRead:
    lesson = await service.create_lesson(user_id=user_id, payload=payload)
    return LessonRead.model_validate(lesson)


@router.get("/{lesson_id}", response_model=LessonRead)
async def get_lesson(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: LessonService = Depends(get_lesson_service),
) -> LessonRead:
    lesson = await service.get_lesson(lesson_id=lesson_id, user_id=user_id)
    return LessonRead.model_validate(lesson)


@router.patch("/{lesson_id}", response_model=LessonRead)
async def update_lesson(
    lesson_id: UUID,
    payload: LessonUpdate,
    user_id: UUID = Depends(get_current_db_user_id),
    service: LessonService = Depends(get_lesson_service),
) -> LessonRead:
    lesson = await service.update_lesson(lesson_id=lesson_id, user_id=user_id, payload=payload)
    return LessonRead.model_validate(lesson)


@router.delete("/{lesson_id}", response_model=MessageResponse)
async def delete_lesson(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_db_user_id),
    service: LessonService = Depends(get_lesson_service),
) -> MessageResponse:
    await service.delete_lesson(lesson_id=lesson_id, user_id=user_id)
    return MessageResponse(message="Lesson deleted")
