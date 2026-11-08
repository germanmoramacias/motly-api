import os
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from alembic import command
from app.modules.analytics.models import QuizResult
from app.modules.quiz.models import QuizAnswer, QuizGenerationJob, QuizQuestion, QuizSession
from app.modules.users.models import User


@unittest.skipUnless(
    os.environ.get("QUIZ_TEST_DATABASE_URL"), "Requires isolated PostgreSQL schemas"
)
class QuizMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_downgrade_upgrade_preserves_quiz_graph_and_legacy_rows(self):
        engine = create_async_engine(os.environ["QUIZ_TEST_DATABASE_URL"])
        schema = "migtest_" + uuid4().hex
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

            def roundtrip(sync):
                config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
                config.attributes["connection"] = sync
                command.upgrade(config, "20260612_0004")
                command.upgrade(config, "20261108_0005")
                with Session(sync) as db:
                    user = User(supabase_user_id="migration-test", email="migration@test.invalid")
                    db.add(user)
                    db.flush()
                    quiz = QuizSession(
                        user_id=user.id,
                        title="Keep this quiz",
                        scope="all",
                        status="completed",
                        question_count=1,
                        idempotency_key="migration",
                        request_fingerprint="x" * 64,
                        context_snapshot=[],
                        completed_at=datetime.now(UTC),
                    )
                    db.add(quiz)
                    db.flush()
                    option = str(uuid4())
                    question = QuizQuestion(
                        session_id=quiz.id,
                        position=0,
                        category="grammar",
                        question="Keep this question",
                        options=[{"id": option, "text": "Yes"}],
                        correct_option_id=option,
                        explanation="Keep this explanation",
                        sources=[],
                    )
                    db.add(question)
                    db.flush()
                    db.add_all(
                        [
                            QuizAnswer(
                                question_id=question.id,
                                selected_option_id=option,
                                is_correct=True,
                                submitted_at=datetime.now(UTC),
                            ),
                            QuizGenerationJob(
                                session_id=quiz.id, status="done", available_at=datetime.now(UTC)
                            ),
                            QuizResult(
                                user_id=user.id,
                                quiz_session_id=quiz.id,
                                score=1,
                                correct_count=1,
                                score_percent=100,
                                total_questions=1,
                            ),
                            QuizResult(user_id=user.id, score=7, total_questions=10),
                        ]
                    )
                    db.flush()
                    quiz_id = quiz.id
                    db.commit()
                command.downgrade(config, "20260612_0004")
                archive = schema + "_quiz_0005_archive"
                self.assertFalse(inspect(sync).has_table("quiz_sessions", schema=schema))
                self.assertTrue(inspect(sync).has_table("quiz_sessions", schema=archive))
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM quiz_results")), 2)
                command.upgrade(config, "20261108_0005")
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM quiz_sessions")), 1)
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM quiz_questions")), 1)
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM quiz_answers")), 1)
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM quiz_generation_jobs")), 1)
                result = sync.execute(
                    text(
                        "SELECT quiz_session_id,score_percent FROM quiz_results "
                        "WHERE correct_count=1"
                    )
                ).one()
                self.assertEqual((result.quiz_session_id, result.score_percent), (quiz_id, 100))
                self.assertEqual(
                    sync.scalar(
                        text("SELECT count(*) FROM quiz_results WHERE quiz_session_id IS NULL")
                    ),
                    1,
                )
                self.assertFalse(inspect(sync).has_schema(archive))

            await connection.run_sync(roundtrip)
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
