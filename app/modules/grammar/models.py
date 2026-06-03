from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GrammarTopic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grammar_topics"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    lesson: Mapped["Lesson"] = relationship(back_populates="grammar_topics")
