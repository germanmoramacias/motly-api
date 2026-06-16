from __future__ import annotations

from pydantic import Field

from app.shared.schemas import AppBaseModel


class ChatMessage(AppBaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class TutorChatRequest(AppBaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class TutorChatResponse(AppBaseModel):
    message: str


class VocabularyExtractionItem(AppBaseModel):
    term: str
    definition: str
    example: str | None = None


class GrammarExtractionItem(AppBaseModel):
    title: str
    content: str
    source_language: str = Field(default="en", min_length=2, max_length=16)


class ExpressionExtractionItem(AppBaseModel):
    text: str
    keyword: str | None = None
    group: str | None = None
    meaning: str
    example: str | None = None


class QuizQuestion(AppBaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_answer: str
    explanation: str


class WritingErrorItem(AppBaseModel):
    error_text: str
    correction: str
    explanation: str
    category: str


class WritingCorrection(AppBaseModel):
    corrected_content: str
    feedback: str
    score: int = Field(ge=0, le=100)
    errors: list[WritingErrorItem] = Field(default_factory=list)
