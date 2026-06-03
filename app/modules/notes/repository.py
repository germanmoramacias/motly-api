from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notes.models import Lesson
from app.modules.notes.schemas import LessonCreate, LessonUpdate


class LessonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: UUID, limit: int, offset: int) -> list[Lesson]:
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.user_id == user_id)
            .order_by(Lesson.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_for_user(self, lesson_id: UUID, user_id: UUID) -> Lesson | None:
        result = await self.session.execute(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, payload: LessonCreate) -> Lesson:
        lesson = Lesson(user_id=user_id, **payload.model_dump())
        self.session.add(lesson)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def update(self, lesson: Lesson, payload: LessonUpdate) -> Lesson:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(lesson, key, value)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def delete(self, lesson: Lesson) -> None:
        await self.session.delete(lesson)
        await self.session.commit()
