from __future__ import annotations

from uuid import UUID

from app.modules.ai.schemas import QuizQuestion
from app.modules.ai.service import OpenAIService
from app.modules.notes.service import LessonService


class QuizService:
    def __init__(self, lessons: LessonService, ai: OpenAIService) -> None:
        self.lessons = lessons
        self.ai = ai

    async def generate_for_lesson(
        self, lesson_id: UUID, user_id: UUID, total_questions: int
    ) -> list[QuizQuestion]:
        lesson = await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        return await self.ai.generate_quiz(text=lesson.content, total_questions=total_questions)
