from __future__ import annotations

from uuid import UUID

from app.modules.analytics.models import QuizResult
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import LearningStats, QuizResultCreate


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    async def create_quiz_result(self, user_id: UUID, payload: QuizResultCreate) -> QuizResult:
        return await self.repository.create_quiz_result(user_id=user_id, payload=payload)

    async def list_quiz_results(self, user_id: UUID, limit: int, offset: int) -> list[QuizResult]:
        return await self.repository.list_quiz_results(user_id=user_id, limit=limit, offset=offset)

    async def get_learning_stats(self, user_id: UUID) -> LearningStats:
        quiz_count, average_score = await self.repository.quiz_summary(user_id)
        return LearningStats(
            lessons_count=await self.repository.count_lessons(user_id),
            vocabulary_count=await self.repository.count_vocabulary(user_id),
            expressions_count=await self.repository.count_expressions(user_id),
            grammar_topics_count=await self.repository.count_grammar_topics(user_id),
            writing_submissions_count=await self.repository.count_writing_submissions(user_id),
            quiz_attempts_count=quiz_count,
            average_quiz_score=average_score,
        )
