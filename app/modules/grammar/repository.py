from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.grammar.models import GrammarTopic
from app.modules.grammar.schemas import GrammarTopicCreate


class GrammarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: UUID, limit: int, offset: int) -> list[GrammarTopic]:
        result = await self.session.execute(
            select(GrammarTopic)
            .where(GrammarTopic.user_id == user_id)
            .order_by(GrammarTopic.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_lesson(self, lesson_id: UUID, user_id: UUID) -> list[GrammarTopic]:
        result = await self.session.execute(
            select(GrammarTopic)
            .where(GrammarTopic.lesson_id == lesson_id, GrammarTopic.user_id == user_id)
            .order_by(GrammarTopic.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: UUID, payload: GrammarTopicCreate) -> GrammarTopic:
        row = GrammarTopic(user_id=user_id, **payload.model_dump())
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def create_many(
        self,
        user_id: UUID,
        items: list[GrammarTopicCreate],
        lesson_id: UUID | None = None,
    ) -> list[GrammarTopic]:
        rows = [
            GrammarTopic(
                user_id=user_id,
                lesson_id=lesson_id if lesson_id is not None else item.lesson_id,
                **item.model_dump(exclude={"lesson_id"}),
            )
            for item in items
        ]
        self.session.add_all(rows)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return rows
