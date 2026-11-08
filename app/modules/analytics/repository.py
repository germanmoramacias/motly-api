from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import QuizResult
from app.modules.analytics.schemas import QuizResultCreate
from app.modules.expressions.models import Expression
from app.modules.grammar.models import GrammarTopic
from app.modules.notes.models import Lesson
from app.modules.vocabulary.models import Vocabulary


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_quiz_result(self, user_id: UUID, payload: QuizResultCreate) -> QuizResult:
        result = QuizResult(user_id=user_id, **payload.model_dump())
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def list_quiz_results(self, user_id: UUID, limit: int, offset: int) -> list[QuizResult]:
        result = await self.session.execute(
            select(QuizResult)
            .where(QuizResult.user_id == user_id)
            .order_by(QuizResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_lessons(self, user_id: UUID) -> int:
        result = await self.session.execute(select(func.count()).select_from(Lesson).where(Lesson.user_id == user_id))
        return int(result.scalar_one())

    async def count_vocabulary(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Vocabulary).where(Vocabulary.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_expressions(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Expression).where(Expression.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_grammar_topics(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(GrammarTopic).where(GrammarTopic.user_id == user_id)
        )
        return int(result.scalar_one())

    async def quiz_summary(self, user_id: UUID) -> tuple[int, float | None]:
        result = await self.session.execute(
            select(func.count(QuizResult.id), func.avg(QuizResult.score_percent))
            .select_from(QuizResult)
            .where(QuizResult.user_id == user_id)
        )
        count, average = result.one()
        return int(count), float(average) if average is not None else None
