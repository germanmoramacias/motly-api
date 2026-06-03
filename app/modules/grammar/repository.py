from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.grammar.models import GrammarTopic
from app.modules.grammar.schemas import GrammarTopicCreate


class GrammarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_lesson(self, lesson_id: UUID) -> list[GrammarTopic]:
        result = await self.session.execute(
            select(GrammarTopic)
            .where(GrammarTopic.lesson_id == lesson_id)
            .order_by(GrammarTopic.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_many(self, lesson_id: UUID, items: list[GrammarTopicCreate]) -> list[GrammarTopic]:
        rows = [GrammarTopic(lesson_id=lesson_id, **item.model_dump()) for item in items]
        self.session.add_all(rows)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return rows
