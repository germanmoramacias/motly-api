from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.expressions.models import Expression
from app.modules.expressions.schemas import ExpressionCreate, ExpressionUpdate
from app.utils.pagination import ExpressionSort


class ExpressionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        lesson_id: UUID | None = None,
        q: str | None = None,
        sort: ExpressionSort = "created_at_desc",
    ) -> tuple[list[Expression], int]:
        query = select(Expression).where(Expression.user_id == user_id)
        if lesson_id is not None:
            query = query.where(Expression.lesson_id == lesson_id)
        if q and (search := q.strip()):
            query = query.where(
                or_(
                    Expression.text.icontains(search, autoescape=True),
                    Expression.meaning.icontains(search, autoescape=True),
                    Expression.example.icontains(search, autoescape=True),
                    Expression.keyword.icontains(search, autoescape=True),
                    Expression.group.icontains(search, autoescape=True),
                )
            )

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        if sort == "text_asc":
            ordering = (func.lower(Expression.text).asc(), Expression.id.asc())
        elif sort == "text_desc":
            ordering = (func.lower(Expression.text).desc(), Expression.id.desc())
        elif sort == "created_at_asc":
            ordering = (Expression.created_at.asc(), Expression.id.asc())
        else:
            ordering = (Expression.created_at.desc(), Expression.id.desc())
        result = await self.session.execute(query.order_by(*ordering).limit(limit).offset(offset))
        return list(result.scalars().all()), total or 0

    async def get_for_user(self, item_id: UUID, user_id: UUID) -> Expression | None:
        result = await self.session.execute(
            select(Expression).where(Expression.id == item_id, Expression.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, payload: ExpressionCreate) -> Expression:
        row = Expression(user_id=user_id, **payload.model_dump())
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def create_many(
        self,
        user_id: UUID,
        items: list[ExpressionCreate],
        lesson_id: UUID | None = None,
    ) -> list[Expression]:
        rows = [
            Expression(
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

    async def update(self, item: Expression, payload: ExpressionUpdate) -> Expression:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: Expression) -> None:
        await self.session.delete(item)
        await self.session.commit()
