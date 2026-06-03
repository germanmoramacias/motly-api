from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocabulary.models import Vocabulary
from app.modules.vocabulary.schemas import VocabularyCreate


class VocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_lesson(self, lesson_id: UUID) -> list[Vocabulary]:
        result = await self.session.execute(
            select(Vocabulary).where(Vocabulary.lesson_id == lesson_id).order_by(Vocabulary.term.asc())
        )
        return list(result.scalars().all())

    async def create_many(self, lesson_id: UUID, items: list[VocabularyCreate]) -> list[Vocabulary]:
        rows = [Vocabulary(lesson_id=lesson_id, **item.model_dump()) for item in items]
        self.session.add_all(rows)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return rows
