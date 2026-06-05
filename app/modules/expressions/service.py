from __future__ import annotations

from uuid import UUID

from app.modules.ai.service import OpenAIService
from app.modules.expressions.models import Expression
from app.modules.expressions.repository import ExpressionRepository
from app.modules.expressions.schemas import ExpressionCreate
from app.modules.notes.service import LessonService


class ExpressionService:
    def __init__(
        self,
        repository: ExpressionRepository,
        lessons: LessonService,
        ai: OpenAIService,
    ) -> None:
        self.repository = repository
        self.lessons = lessons
        self.ai = ai

    async def list_for_user(self, user_id: UUID, limit: int, offset: int) -> list[Expression]:
        return await self.repository.list_by_user(user_id=user_id, limit=limit, offset=offset)

    async def list_for_lesson(self, lesson_id: UUID, user_id: UUID) -> list[Expression]:
        await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        return await self.repository.list_by_lesson(lesson_id=lesson_id, user_id=user_id)

    async def create_item(self, user_id: UUID, payload: ExpressionCreate) -> Expression:
        if payload.lesson_id is not None:
            await self.lessons.get_lesson(lesson_id=payload.lesson_id, user_id=user_id)
        return await self.repository.create(user_id=user_id, payload=payload)

    async def extract_for_lesson(self, lesson_id: UUID, user_id: UUID) -> list[Expression]:
        lesson = await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        extracted = await self.ai.extract_expressions(lesson.content)
        payload = [ExpressionCreate.model_validate(item.model_dump()) for item in extracted]
        return await self.repository.create_many(user_id=user_id, lesson_id=lesson.id, items=payload)
