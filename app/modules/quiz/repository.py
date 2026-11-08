from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.expressions.models import Expression
from app.modules.grammar.models import GrammarTopic
from app.modules.notes.models import Lesson
from app.modules.quiz.content import build_snapshot
from app.modules.quiz.models import PENDING_STATUSES, QuizAnswer, QuizQuestion, QuizSession
from app.modules.users.models import User
from app.modules.vocabulary.models import Vocabulary


class QuizRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self):
        # Authentication may already have opened this request's transaction.
        try:
            yield
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def lock_user(self, user_id: UUID) -> User:
        return (
            await self.session.execute(select(User).where(User.id == user_id).with_for_update())
        ).scalar_one()

    async def get(
        self, session_id: UUID, user_id: UUID, *, lock: bool = False
    ) -> QuizSession | None:
        query = select(QuizSession).where(
            QuizSession.id == session_id, QuizSession.user_id == user_id
        )
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def active(self, user_id: UUID) -> QuizSession | None:
        return (
            await self.session.execute(
                select(QuizSession).where(
                    QuizSession.user_id == user_id, QuizSession.status.in_(PENDING_STATUSES)
                )
            )
        ).scalar_one_or_none()

    async def by_key(self, user_id: UUID, key: str) -> QuizSession | None:
        return (
            await self.session.execute(
                select(QuizSession).where(
                    QuizSession.user_id == user_id, QuizSession.idempotency_key == key
                )
            )
        ).scalar_one_or_none()

    async def questions(self, session_id: UUID):
        return (
            await self.session.execute(
                select(QuizQuestion, QuizAnswer)
                .outerjoin(QuizAnswer, QuizAnswer.question_id == QuizQuestion.id)
                .where(QuizQuestion.session_id == session_id)
                .order_by(QuizQuestion.position)
            )
        ).all()

    async def history(self, user_id: UUID, limit: int, offset: int):
        predicate = (QuizSession.user_id == user_id, QuizSession.status == "completed")
        total = await self.session.scalar(
            select(func.count()).select_from(QuizSession).where(*predicate)
        )
        rows = (
            await self.session.execute(
                select(
                    QuizSession,
                    func.count(QuizAnswer.id),
                    func.coalesce(func.sum(case((QuizAnswer.is_correct.is_(True), 1), else_=0)), 0),
                )
                .outerjoin(QuizQuestion, QuizQuestion.session_id == QuizSession.id)
                .outerjoin(QuizAnswer, QuizAnswer.question_id == QuizQuestion.id)
                .where(*predicate)
                .group_by(QuizSession.id)
                .order_by(QuizSession.completed_at.desc(), QuizSession.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return rows, total or 0

    async def lesson_options(self, user_id: UUID, q: str, limit: int, offset: int):
        predicate = [Lesson.user_id == user_id]
        if q:
            predicate.append(Lesson.title.icontains(q, autoescape=True))
        total = await self.session.scalar(
            select(func.count()).select_from(Lesson).where(*predicate)
        )
        rows = (
            await self.session.execute(
                select(Lesson.id, Lesson.title)
                .where(*predicate)
                .order_by(Lesson.updated_at.desc(), Lesson.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return rows, total or 0

    async def snapshot(self, user_id: UUID, lesson_id: UUID | None, seed: UUID, budget: int):
        recent = (
            await self.session.scalars(
                select(QuizSession.context_snapshot)
                .where(QuizSession.user_id == user_id)
                .order_by(QuizSession.created_at.desc())
                .limit(5)
            )
        ).all()
        recent_ids = [source["id"].split(":", 1)[-1] for context in recent for source in context]
        groups: list[list[dict]] = []
        for model, kind in (
            (Lesson, "lesson"),
            (GrammarTopic, "grammar"),
            (Vocabulary, "vocabulary"),
            (Expression, "expression"),
        ):
            query = select(model).where(model.user_id == user_id)
            if lesson_id is not None:
                query = query.where((model.id if model is Lesson else model.lesson_id) == lesson_id)
            if recent_ids:
                query = query.order_by(case((cast(model.id, String).in_(recent_ids), 1), else_=0))
            query = query.order_by(func.md5(func.concat(cast(model.id, String), str(seed)))).limit(
                60
            )
            entries = (await self.session.scalars(query)).all()
            group = []
            for item in entries:
                if kind in ("lesson", "grammar"):
                    title, content = item.title, item.content
                elif kind == "vocabulary":
                    title = item.term
                    content = f"{item.term}: {item.definition}. {item.example or ''}"
                else:
                    title = item.text
                    content = f"{item.text}: {item.meaning}. {item.example or ''}"
                group.append(
                    {
                        "id": f"{kind}:{item.id}",
                        "kind": kind,
                        "title": title,
                        "content": content,
                        "updated_at": item.updated_at.isoformat(),
                    }
                )
            groups.append(group)
        return build_snapshot(groups, budget)
