from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocabulary.models import Vocabulary
from app.modules.vocabulary.schemas import VocabularyCreate, VocabularyUpdate


class VocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        lesson_id: UUID | None = None,
    ) -> list[Vocabulary]:
        query = select(Vocabulary).where(Vocabulary.user_id == user_id)
        if lesson_id is not None:
            query = query.where(Vocabulary.lesson_id == lesson_id)

        result = await self.session.execute(
            query.order_by(Vocabulary.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_for_user(self, item_id: UUID, user_id: UUID) -> Vocabulary | None:
        result = await self.session.execute(
            select(Vocabulary).where(Vocabulary.id == item_id, Vocabulary.user_id == user_id)
        )
        return result.scalar_one_or_none()

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

    async def update(self, item: Vocabulary, payload: VocabularyUpdate) -> Vocabulary:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: Vocabulary) -> None:
        await self.session.delete(item)
        await self.session.commit()
