"""Run with python -m app.modules.quiz.worker. Jobs survive API/worker restarts."""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, dispose_engine
from app.modules.analytics.models import QuizResult  # noqa: F401 - register FK metadata
from app.modules.expressions.models import Expression  # noqa: F401
from app.modules.grammar.models import GrammarTopic  # noqa: F401
from app.modules.notes.models import Lesson  # noqa: F401
from app.modules.quiz.generator import generate
from app.modules.quiz.models import QuizGenerationJob, QuizQuestion, QuizSession
from app.modules.users.models import User
from app.modules.vocabulary.models import Vocabulary  # noqa: F401

logger = logging.getLogger(__name__)


async def claim() -> dict | None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db, db.begin():
        job = (
            await db.execute(
                select(QuizGenerationJob)
                .join(QuizSession, QuizSession.id == QuizGenerationJob.session_id)
                .where(
                    QuizSession.status == "generating",
                    or_(
                        and_(
                            QuizGenerationJob.status == "queued",
                            QuizGenerationJob.available_at <= now,
                        ),
                        and_(
                            QuizGenerationJob.status == "running",
                            QuizGenerationJob.lease_until <= now,
                        ),
                    ),
                )
                .order_by(QuizGenerationJob.available_at, QuizGenerationJob.id)
                .with_for_update(skip_locked=True, of=QuizGenerationJob)
                .limit(1)
            )
        ).scalar_one_or_none()
        if job is None:
            return None
        session = await db.get(QuizSession, job.session_id)
        user = await db.get(User, session.user_id)
        job.status = "running"
        job.attempts += 1
        job.lease_token = uuid4()
        job.lease_until = now + timedelta(seconds=settings.quiz_generation_timeout_seconds + 30)
        return {
            "id": job.id,
            "session_id": session.id,
            "token": job.lease_token,
            "context": session.context_snapshot,
            "level": session.english_level,
            "language": next(iter(user.source_languages or []), "es"),
            "attempts": job.attempts,
        }


async def publish(work: dict, quiz=None) -> bool:
    async with AsyncSessionLocal() as db, db.begin():
        session = (
            await db.execute(
                select(QuizSession).where(QuizSession.id == work["session_id"]).with_for_update()
            )
        ).scalar_one_or_none()
        if session is None or session.status != "generating":
            return False
        job = (
            await db.execute(
                select(QuizGenerationJob)
                .where(QuizGenerationJob.id == work["id"])
                .with_for_update()
            )
        ).scalar_one_or_none()
        if job is None or job.lease_token != work["token"] or job.status != "running":
            return False  # An expired worker must never overwrite another worker's result.
        if quiz is None:
            if job.attempts >= settings.quiz_generation_max_attempts:
                job.status = "failed"
                session.status = "generation_failed"
                session.error_code = "GENERATION_FAILED"
            else:
                job.status = "queued"
                job.available_at = datetime.now(UTC) + timedelta(seconds=3 * job.attempts)
        else:
            sources = {s["id"]: {k: s[k] for k in ("id", "kind", "title")} for s in work["context"]}
            for position, question in enumerate(quiz.questions):
                options = [{"id": str(uuid4()), "text": text.strip()} for text in question.options]
                db.add(
                    QuizQuestion(
                        session_id=session.id,
                        position=position,
                        category=question.category,
                        question=question.question,
                        options=options,
                        correct_option_id=options[question.correct_index]["id"],
                        explanation=question.explanation,
                        sources=[sources[source] for source in dict.fromkeys(question.source_ids)],
                    )
                )
            session.question_count = len(quiz.questions)
            session.model = settings.openai_model
            session.status = "in_progress"
            session.error_code = None
            job.status = "done"
        job.lease_token = None
        job.lease_until = None
        return True


async def run_once() -> bool:
    work = await claim()
    if work is None:
        return False
    quiz = None
    try:
        if work["attempts"] <= settings.quiz_generation_max_attempts:
            quiz = await asyncio.wait_for(
                generate(
                    work["context"], work["level"], settings.quiz_max_questions, work["language"]
                ),
                timeout=settings.quiz_generation_timeout_seconds,
            )
    except Exception as exc:
        # Do not log study material, provider payloads or credentials.
        logger.warning(
            "Quiz generation failed: job=%s error_type=%s", work["id"], type(exc).__name__
        )
    await publish(work, quiz)
    return True


async def main() -> None:
    logging.basicConfig(level=settings.log_level)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    try:
        while not stop.is_set():
            try:
                busy = await run_once()
            except Exception:
                logger.exception("Quiz worker database operation failed")
                busy = False
            if not busy:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=settings.quiz_worker_poll_seconds)
                except TimeoutError:
                    pass
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
