import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.quiz.generator import generate
from app.modules.quiz.schemas import GeneratedQuiz


class GeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_parsing_source_validation_and_client_cleanup(self):
        client = MagicMock()
        client.close = AsyncMock()
        parse = AsyncMock()
        client.with_options.return_value.chat.completions.parse = parse
        output = GeneratedQuiz.model_validate(
            {
                "questions": [
                    {
                        "category": "vocabulary",
                        "question": "Which means gato?",
                        "options": ["Cat", "Dog"],
                        "correct_index": 0,
                        "explanation": "Cat means gato.",
                        "source_ids": ["vocabulary:known"],
                    }
                ]
            }
        )
        parse.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=output))]
        )
        context = [{"id": "vocabulary:known", "content": "cat: gato"}]
        with patch(
            "app.modules.quiz.generator.OpenAIService", return_value=SimpleNamespace(client=client)
        ):
            self.assertEqual(await generate(context, "B1", 15, "es"), output)
            kwargs = parse.call_args.kwargs
            self.assertEqual(kwargs["response_format"], GeneratedQuiz)
            self.assertIn("B1", kwargs["messages"][0]["content"])
            self.assertNotIn("cat: gato", kwargs["messages"][0]["content"])
            self.assertIn("cat: gato", kwargs["messages"][1]["content"])
            output.questions[0].source_ids = ["vocabulary:unknown"]
            with self.assertRaises(ValueError):
                await generate(context, None, 15, "es")
            parse.return_value.choices[0].message.parsed = None
            with self.assertRaises(ValueError):
                await generate(context, None, 15, "es")
        self.assertEqual(client.close.await_count, 3)
