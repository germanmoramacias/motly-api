from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Expression(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expressions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), index=True
    )
    text: Mapped[str] = mapped_column(String(180), nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(120))
    group: Mapped[str | None] = mapped_column("group", String(80))
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="expressions")
    lesson: Mapped["Lesson"] = relationship(back_populates="expressions")
