from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocabulary.models import Vocabulary
from app.modules.vocabulary.schemas import VocabularyCreate


class VocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: UUID, limit: int, offset: int) -> list[Vocabulary]:
        result = await self.session.execute(
            select(Vocabulary)
            .where(Vocabulary.user_id == user_id)
            .order_by(Vocabulary.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_lesson(self, lesson_id: UUID, user_id: UUID) -> list[Vocabulary]:
        result = await self.session.execute(
            select(Vocabulary)
            .where(Vocabulary.lesson_id == lesson_id, Vocabulary.user_id == user_id)
            .order_by(Vocabulary.term.asc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: UUID, payload: VocabularyCreate) -> Vocabulary:
        row = Vocabulary(user_id=user_id, **payload.model_dump())
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def create_many(
        self,
        user_id: UUID,
        items: list[VocabularyCreate],
        lesson_id: UUID | None = None,
    ) -> list[Vocabulary]:
        rows = [
            Vocabulary(
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
