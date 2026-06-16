from __future__ import annotations

from uuid import UUID

from app.core.errors import NotFoundError
from app.modules.grammar.models import GrammarTopic
from app.modules.grammar.repository import GrammarRepository
from app.modules.grammar.schemas import GrammarTopicCreate, GrammarTopicUpdate
from app.modules.notes.service import LessonService


class GrammarService:
    def __init__(self, repository: GrammarRepository, lessons: LessonService) -> None:
        self.repository = repository
        self.lessons = lessons

    async def list_for_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        lesson_id: UUID | None = None,
    ) -> list[GrammarTopic]:
        if lesson_id is not None:
            await self.lessons.get_lesson(lesson_id=lesson_id, user_id=user_id)
        return await self.repository.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            lesson_id=lesson_id,
        )

    async def get_topic(self, item_id: UUID, user_id: UUID) -> GrammarTopic:
        item = await self.repository.get_for_user(item_id=item_id, user_id=user_id)
        if item is None:
            raise NotFoundError("Grammar topic not found")
        return item

    async def create_topic(self, user_id: UUID, payload: GrammarTopicCreate) -> GrammarTopic:
        if payload.lesson_id is not None:
            await self.lessons.get_lesson(lesson_id=payload.lesson_id, user_id=user_id)
        return await self.repository.create(user_id=user_id, payload=payload)

    async def update_topic(
        self,
        item_id: UUID,
        user_id: UUID,
        payload: GrammarTopicUpdate,
    ) -> GrammarTopic:
        item = await self.get_topic(item_id=item_id, user_id=user_id)
        if payload.lesson_id is not None:
            await self.lessons.get_lesson(lesson_id=payload.lesson_id, user_id=user_id)
        return await self.repository.update(item=item, payload=payload)

    async def delete_topic(self, item_id: UUID, user_id: UUID) -> None:
        item = await self.get_topic(item_id=item_id, user_id=user_id)
        await self.repository.delete(item)
