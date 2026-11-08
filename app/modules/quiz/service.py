from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.modules.analytics.models import QuizResult
from app.modules.notes.models import Lesson
from app.modules.quiz.models import QuizAnswer, QuizGenerationJob, QuizSession
from app.modules.quiz.repository import QuizRepository
from app.modules.quiz.schemas import (
    AnswerCreate,
    AnswerRead,
    QuestionRead,
    SessionCreate,
    SessionRead,
    SessionSummary,
)


def summary(session: QuizSession, answered: int, correct: int) -> SessionSummary:
    return SessionSummary(
        id=session.id,
        title=session.title,
        scope=session.scope,
        lesson_id=session.lesson_id,
        status=session.status,
        question_count=session.question_count,
        answered_count=answered,
        correct_count=correct,
        score_percent=100 * correct / session.question_count
        if session.status == "completed" and session.question_count
        else None,
        created_at=session.created_at,
        completed_at=session.completed_at,
        error_code=session.error_code,
    )


class QuizService:
    def __init__(self, repository: QuizRepository) -> None:
        self.repo = repository

    async def read(self, session: QuizSession) -> SessionRead:
        rows = await self.repo.questions(session.id)
        answers = [
            AnswerRead(
                question=QuestionRead.model_validate(question),
                selected_option_id=answer.selected_option_id,
                correct_option_id=question.correct_option_id,
                is_correct=answer.is_correct,
                explanation=question.explanation,
                sources=question.sources,
                submitted_at=answer.submitted_at,
            )
            for question, answer in rows
            if answer is not None
        ]
        current = next((QuestionRead.model_validate(q) for q, a in rows if a is None), None)
        return SessionRead(
            **summary(session, len(answers), sum(a.is_correct for a in answers)).model_dump(),
            current_question=current,
            answers=answers,
        )

    async def get(self, session_id: UUID, user_id: UUID) -> SessionRead:
        session = await self.repo.get(session_id, user_id)
        if session is None:
            raise NotFoundError("Quiz not found")
        return await self.read(session)

    async def active(self, user_id: UUID) -> SessionRead | None:
        session = await self.repo.active(user_id)
        return await self.read(session) if session else None

    async def create(self, user_id: UUID, payload: SessionCreate, key: str) -> SessionRead:
        fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
        async with self.repo.transaction():
            user = await self.repo.lock_user(user_id)
            previous = await self.repo.by_key(user_id, key)
            if previous:
                if previous.request_fingerprint != fingerprint:
                    raise AppError(
                        "This request key was already used for another quiz.",
                        409,
                        code="IDEMPOTENCY_CONFLICT",
                    )
                return await self.read(previous)
            active = await self.repo.active(user_id)
            if active:
                raise AppError(
                    "Continue your pending quiz before creating another.",
                    409,
                    code="ACTIVE_QUIZ_EXISTS",
                    details={"session_id": str(active.id)},
                )
            title = "All my material"
            if payload.lesson_id:
                lesson = (
                    await self.repo.session.execute(
                        select(Lesson).where(
                            Lesson.id == payload.lesson_id, Lesson.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                if lesson is None:
                    raise NotFoundError("Lesson not found")
                title = lesson.title
            session_id = uuid4()
            context = await self.repo.snapshot(
                user_id, payload.lesson_id, session_id, settings.quiz_context_chars
            )
            if not context:
                raise AppError(
                    "There is not enough text to create a quiz. Add notes, vocabulary, "
                    "grammar or expressions first. Image-only notes cannot be used yet.",
                    422,
                    code="INSUFFICIENT_CONTENT",
                )
            session = QuizSession(
                id=session_id,
                user_id=user_id,
                scope=payload.scope,
                lesson_id=payload.lesson_id,
                title=title,
                idempotency_key=key,
                request_fingerprint=fingerprint,
                context_snapshot=context,
                english_level=user.english_level,
                status="generating",
                question_count=0,
            )
            self.repo.session.add(session)
            await self.repo.session.flush()
            self.repo.session.add(
                QuizGenerationJob(session_id=session.id, available_at=datetime.now(UTC))
            )
            await self.repo.session.flush()
            result = await self.read(session)
        return result

    async def answer(self, session_id: UUID, user_id: UUID, payload: AnswerCreate) -> SessionRead:
        async with self.repo.transaction():
            session = await self.repo.get(session_id, user_id, lock=True)
            if session is None:
                raise NotFoundError("Quiz not found")
            rows = await self.repo.questions(session.id)
            match = next(((q, a) for q, a in rows if q.id == payload.question_id), None)
            if match is None:
                raise NotFoundError("Question not found")
            question, previous = match
            option = str(payload.selected_option_id)
            if previous:
                if previous.selected_option_id != option:
                    raise AppError(
                        "This question has already been answered.",
                        409,
                        code="ANSWER_ALREADY_SUBMITTED",
                    )
                return await self.read(session)
            if session.status != "in_progress":
                raise AppError("This quiz is not accepting answers.", 409, code="QUIZ_NOT_READY")
            current = next(q for q, a in rows if a is None)
            if current.id != question.id:
                raise AppError(
                    "Answer the current question first.", 409, code="QUESTION_OUT_OF_ORDER"
                )
            if option not in {o["id"] for o in question.options}:
                raise AppError("Choose one of this question's options.", 422, code="INVALID_OPTION")
            correct = option == question.correct_option_id
            self.repo.session.add(
                QuizAnswer(
                    question_id=question.id,
                    selected_option_id=option,
                    is_correct=correct,
                    submitted_at=datetime.now(UTC),
                )
            )
            answered = sum(a is not None for _, a in rows) + 1
            if answered == session.question_count:
                correct_count = sum(a.is_correct for _, a in rows if a is not None) + int(correct)
                session.status = "completed"
                session.completed_at = datetime.now(UTC)
                self.repo.session.add(
                    QuizResult(
                        user_id=user_id,
                        lesson_id=session.lesson_id,
                        quiz_session_id=session.id,
                        score=correct_count,
                        correct_count=correct_count,
                        score_percent=100 * correct_count / session.question_count,
                        total_questions=session.question_count,
                        result_metadata={"version": 2},
                    )
                )
            await self.repo.session.flush()
            result = await self.read(session)
        return result

    async def retry(self, session_id: UUID, user_id: UUID) -> SessionRead:
        async with self.repo.transaction():
            session = await self.repo.get(session_id, user_id, lock=True)
            if session is None:
                raise NotFoundError("Quiz not found")
            if session.status == "generation_failed":
                job = (
                    await self.repo.session.execute(
                        select(QuizGenerationJob)
                        .where(QuizGenerationJob.session_id == session.id)
                        .with_for_update()
                    )
                ).scalar_one()
                job.status = "queued"
                job.attempts = 0
                job.available_at = datetime.now(UTC)
                job.lease_token = None
                job.lease_until = None
                session.status = "generating"
                session.error_code = None
                await self.repo.session.flush()
            return await self.read(session)
