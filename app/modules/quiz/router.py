from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.ai.router import get_openai_service
from app.modules.ai.service import OpenAIService
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.modules.quiz.schemas import QuizGenerateRequest, QuizGenerateResponse
from app.modules.quiz.service import QuizService

router = APIRouter()


def get_quiz_service(
    lessons: LessonService = Depends(get_lesson_service),
    ai: OpenAIService = Depends(get_openai_service),
) -> QuizService:
    return QuizService(lessons, ai)


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(
    payload: QuizGenerateRequest,
    user_id: UUID = Depends(get_current_db_user_id),
    service: QuizService = Depends(get_quiz_service),
) -> QuizGenerateResponse:
    questions = await service.generate_for_lesson(
        lesson_id=payload.lesson_id,
        user_id=user_id,
        total_questions=payload.total_questions,
    )
    return QuizGenerateResponse(questions=questions)
