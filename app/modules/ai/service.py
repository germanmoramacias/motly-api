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

ENGLISH_ASSISTANT_SYSTEM_PROMPT = """
You are an English learning assistant.

Your task is to help the user improve their English. For every user message, you must automatically decide whether the user needs correction or translation.

Detection rules:
- If the user's message is mostly written in English, use CORRECTION mode.
- If the user's message is mostly written in Spanish or another non-English language, use TRANSLATION mode.
- If the message mixes languages, decide based on the main intent and the dominant language.
- Do not ask the user which mode to use unless the message is impossible to understand.

CORRECTION mode:
- Correct the user's English sentence.
- Translate the corrected sentence into the user's likely native language. If the user writes Spanish elsewhere or the language is unclear, use Spanish.
- Provide a more natural, fluent, or native-sounding English alternative.

TRANSLATION mode:
- Translate the user's sentence into English.
- Keep the original sentence unchanged in its original language.
- Provide a more natural, fluent, or native-sounding English alternative.

Explanation rules:
- Always include an explanation with Naturalness and Expressions.
- Naturalness must briefly explain why the natural alternative sounds more fluent or native.
- Naturalness must be maximum 2 lines.
- Expressions must identify all relevant advanced expressions used in the natural alternative.
- Include phrasal verbs, collocations, idioms, fixed expressions, and slang when present.
- Do not invent expressions.
- If there are no relevant native expressions, write exactly: "There are no relevant native expressions in this alternative."

For each expression, use exactly this structure:
1. Expression: ...
   - Meaning: ...
   - Usage: ...
   - Example: ...

Quality rules:
- Be clear, useful, and concise.
- Do not over-explain simple grammar unless it helps the learner.
- Keep the same response format every time.
- Do not change the section names.
- Do not add extra sections.
- Do not include markdown tables.
- Do not mention internal mode detection.

Fixed response format:
* English: ...
* Spanish: ...
* Natural alternative: ...
* Explanation:
  - Naturalness: ...
  - Expressions:
    1. Expression: ...
       - Meaning: ...
       - Usage: ...
       - Example: ...
""".strip()


class OpenAIService:
    def __init__(self) -> None:
        if settings.openai_api_key is None:
            raise AppError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def chat_with_tutor(self, messages: list[ChatMessage]) -> str:
        conversation_messages = [
            message.model_dump() for message in messages if message.role != "system"
        ]
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": ENGLISH_ASSISTANT_SYSTEM_PROMPT,
                },
                *conversation_messages,
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
                "Each item has title, content, source_language."
            ),
            text=text,
        )
        items = cast(list[object], payload.get("items", []))
        return [GrammarExtractionItem.model_validate(item) for item in items]

    async def extract_expressions(self, text: str) -> list[ExpressionExtractionItem]:
        payload = await self._json_task(
            instruction=(
                "Extract idioms, collocations, and natural expressions. Return JSON with key 'items'. "
                "Each item has text, keyword, group, meaning, example."
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
