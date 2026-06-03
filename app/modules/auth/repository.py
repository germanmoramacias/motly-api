from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.repository import UserRepository


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
