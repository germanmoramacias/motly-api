from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocabulary.models import Vocabulary
from app.modules.vocabulary.schemas import VocabularyCreate, VocabularyUpdate
from app.utils.pagination import VocabularySort


class VocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        lesson_id: UUID | None = None,
        q: str | None = None,
        sort: VocabularySort = "created_at_desc",
    ) -> tuple[list[Vocabulary], int]:
        query = select(Vocabulary).where(Vocabulary.user_id == user_id)
        if lesson_id is not None:
            query = query.where(Vocabulary.lesson_id == lesson_id)
        if q and (search := q.strip()):
            query = query.where(
                or_(
                    Vocabulary.term.icontains(search, autoescape=True),
                    Vocabulary.definition.icontains(search, autoescape=True),
                    Vocabulary.example.icontains(search, autoescape=True),
                )
            )

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        if sort == "term_asc":
            ordering = (func.lower(Vocabulary.term).asc(), Vocabulary.id.asc())
        elif sort == "term_desc":
            ordering = (func.lower(Vocabulary.term).desc(), Vocabulary.id.desc())
        elif sort == "created_at_asc":
            ordering = (Vocabulary.created_at.asc(), Vocabulary.id.asc())
        else:
            ordering = (Vocabulary.created_at.desc(), Vocabulary.id.desc())
        result = await self.session.execute(query.order_by(*ordering).limit(limit).offset(offset))
        return list(result.scalars().all()), total or 0

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
