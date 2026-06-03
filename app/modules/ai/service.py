from __future__ import annotations

import json
from typing import cast

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError
from app.modules.ai.schemas import (
    ChatMessage,
    ExpressionExtractionItem,
    GrammarExtractionItem,
    QuizQuestion,
    WritingCorrection,
    VocabularyExtractionItem,
)


class OpenAIService:
    def __init__(self) -> None:
        if settings.openai_api_key is None:
            raise AppError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def chat_with_tutor(self, messages: list[ChatMessage]) -> str:
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise, encouraging English tutor.",
                },
                *[message.model_dump() for message in messages],
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content or ""

    async def extract_vocabulary(self, text: str) -> list[VocabularyExtractionItem]:
        payload = await self._json_task(
            instruction=(
                "Extract useful English vocabulary. Return JSON with key 'items'. "
                "Each item has term, definition, example, difficulty."
            ),
            text=text,
        )
        items = cast(list[object], payload.get("items", []))
        return [VocabularyExtractionItem.model_validate(item) for item in items]

    async def extract_grammar(self, text: str) -> list[GrammarExtractionItem]:
        payload = await self._json_task(
            instruction=(
                "Extract grammar topics from the text. Return JSON with key 'items'. "
                "Each item has name, explanation, examples."
            ),
            text=text,
        )
        items = cast(list[object], payload.get("items", []))
        return [GrammarExtractionItem.model_validate(item) for item in items]

    async def extract_expressions(self, text: str) -> list[ExpressionExtractionItem]:
        payload = await self._json_task(
            instruction=(
                "Extract idioms, collocations, and natural expressions. Return JSON with key 'items'. "
                "Each item has text, meaning, example."
            ),
            text=text,
        )
        items = cast(list[object], payload.get("items", []))
        return [ExpressionExtractionItem.model_validate(item) for item in items]

    async def generate_quiz(self, text: str, total_questions: int) -> list[QuizQuestion]:
        payload = await self._json_task(
            instruction=(
                f"Create {total_questions} multiple-choice English learning questions. "
                "Return JSON with key 'questions'. Each question has question, options, "
                "correct_answer, explanation."
            ),
            text=text,
        )
        questions = cast(list[object], payload.get("questions", []))
        return [QuizQuestion.model_validate(question) for question in questions]

    async def correct_writing(self, content: str, prompt: str | None) -> WritingCorrection:
        prompt_text = prompt or "No writing prompt was provided."
        payload = await self._json_task(
            instruction=(
                "Correct this English writing submission. Return JSON with corrected_content, "
                "feedback, score from 0 to 100, and errors. Each error has error_text, "
                "correction, explanation, category."
            ),
            text=f"Prompt: {prompt_text}\nSubmission: {content}",
        )
        return WritingCorrection.model_validate(payload)

    async def _json_task(self, instruction: str, text: str) -> dict[str, object]:
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": f"{instruction}\n\nText:\n{text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return cast(dict[str, object], json.loads(content))
