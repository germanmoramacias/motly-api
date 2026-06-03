from __future__ import annotations

from uuid import UUID

from app.core.errors import NotFoundError
from app.modules.notes.models import Lesson
from app.modules.notes.repository import LessonRepository
from app.modules.notes.schemas import LessonCreate, LessonUpdate


class LessonService:
    def __init__(self, repository: LessonRepository) -> None:
        self.repository = repository

    async def list_lessons(self, user_id: UUID, limit: int, offset: int) -> list[Lesson]:
        return await self.repository.list_by_user(user_id=user_id, limit=limit, offset=offset)

    async def get_lesson(self, lesson_id: UUID, user_id: UUID) -> Lesson:
        lesson = await self.repository.get_for_user(lesson_id=lesson_id, user_id=user_id)
        if lesson is None:
            raise NotFoundError("Lesson not found")
        return lesson

    async def create_lesson(self, user_id: UUID, payload: LessonCreate) -> Lesson:
        return await self.repository.create(user_id=user_id, payload=payload)

    async def update_lesson(self, lesson_id: UUID, user_id: UUID, payload: LessonUpdate) -> Lesson:
        lesson = await self.get_lesson(lesson_id=lesson_id, user_id=user_id)
        return await self.repository.update(lesson=lesson, payload=payload)

    async def delete_lesson(self, lesson_id: UUID, user_id: UUID) -> None:
        lesson = await self.get_lesson(lesson_id=lesson_id, user_id=user_id)
        await self.repository.delete(lesson)
