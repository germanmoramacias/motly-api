from __future__ import annotations

from uuid import UUID

from app.modules.ai.service import OpenAIService
from app.modules.notes.service import LessonService
from app.modules.vocabulary.models import Vocabulary
from app.modules.vocabulary.repository import VocabularyRepository
from app.modules.vocabulary.schemas import VocabularyCreate


class VocabularyService:
    def __init__(
        self,
        repository: VocabularyRepository,
        lessons: LessonService,
        ai: OpenAIService,
    ) -> None:
        self.repository = repository
        self.lessons = lessons
        self.ai = ai

    async def list_for_lesson(self, lesson_id: UUID, user_id: UUID) -> list[Vocabulary]:
        await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        return await self.repository.list_by_lesson(lesson_id)

    async def extract_for_lesson(self, lesson_id: UUID, user_id: UUID) -> list[Vocabulary]:
        lesson = await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        extracted = await self.ai.extract_vocabulary(lesson.content)
        payload = [VocabularyCreate.model_validate(item.model_dump()) for item in extracted]
        return await self.repository.create_many(lesson_id=lesson.id, items=payload)
