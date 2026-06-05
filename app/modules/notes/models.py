from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lessons"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)

    user: Mapped["User"] = relationship(back_populates="lessons")
    vocabulary_items: Mapped[list["Vocabulary"]] = relationship(back_populates="lesson")
    expressions: Mapped[list["Expression"]] = relationship(back_populates="lesson")
    grammar_topics: Mapped[list["GrammarTopic"]] = relationship(back_populates="lesson")
