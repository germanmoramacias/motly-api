from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.compiler import Compiled

from app.core.routing import api_v1_router
from app.db.session import get_db_session
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
LESSON_ID = UUID("00000000-0000-0000-0000-000000000002")
SEARCH_FIELDS = {
    "vocabulary": ("term", "definition", "example"),
    "expressions": ("text", "meaning", "example", "keyword", "group"),
}


class CatalogSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session = AsyncSession()
        self.addAsyncCleanup(self.session.close)
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        self.execute = AsyncMock(return_value=result)
        execute_patch = patch.object(self.session, "execute", self.execute)
        execute_patch.start()
        self.addCleanup(execute_patch.stop)
        self.lessons = MagicMock(spec=LessonService)

        async def current_user() -> UUID:
            return USER_ID

        async def session_dependency() -> AsyncSession:
            return self.session

        async def lessons_dependency() -> LessonService:
            return self.lessons

        app = FastAPI()
        app.include_router(api_v1_router, prefix="/api/v1")
        app.dependency_overrides[get_current_db_user_id] = current_user
        app.dependency_overrides[get_db_session] = session_dependency
        app.dependency_overrides[get_lesson_service] = lessons_dependency
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def request(self, catalog: str, params: dict[str, str]) -> Response:
        self.execute.reset_mock()
        self.lessons.reset_mock()
        return await self.client.get(f"/api/v1/{catalog}", params=params)

    def compiled_query(self) -> Compiled:
        self.execute.assert_awaited_once()
        return self.execute.call_args.args[0].compile(dialect=postgresql.dialect())

    async def test_search_covers_all_fields_and_preserves_filters(self) -> None:
        for catalog, fields in SEARCH_FIELDS.items():
            with self.subTest(catalog=catalog):
                response = await self.request(
                    catalog,
                    {"q": "  HoRsE  ", "lesson_id": str(LESSON_ID), "limit": "25", "offset": "50"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])
                self.lessons.get_lesson.assert_awaited_once_with(
                    lesson_id=LESSON_ID, user_id=USER_ID
                )
                compiled = self.compiled_query()
                sql = str(compiled)
                params = compiled.params or {}
                where = sql.split("WHERE ", 1)[1].split(" ORDER BY", 1)[0]
                for field in fields:
                    column = f'"{field}"' if field == "group" else field
                    self.assertIn(f"{catalog}.{column} ILIKE", where)
                    self.assertEqual(params[f"{field}_1"], "HoRsE")
                self.assertEqual(where.count(" OR "), len(fields) - 1)
                self.assertIn(f"{catalog}.user_id =", where)
                self.assertIn(f"{catalog}.lesson_id =", where)
                self.assertEqual(params["user_id_1"], USER_ID)
                self.assertEqual(params["lesson_id_1"], LESSON_ID)
                self.assertIn(f"ORDER BY {catalog}.created_at DESC", sql)
                self.assertIn(25, params.values())
                self.assertIn(50, params.values())

    async def test_omitted_empty_or_blank_search_preserves_existing_listing(self) -> None:
        for catalog in SEARCH_FIELDS:
            for params in ({}, {"q": ""}, {"q": "   "}):
                with self.subTest(catalog=catalog, params=params):
                    response = await self.request(catalog, params)
                    self.assertEqual(response.status_code, 200)
                    compiled = self.compiled_query()
                    where = str(compiled).split("WHERE ", 1)[1].split(" ORDER BY", 1)[0]
                    self.assertNotIn("ILIKE", where)
                    self.assertNotIn(f"{catalog}.lesson_id =", where)
                    self.assertEqual((compiled.params or {})["user_id_1"], USER_ID)
                    self.assertIn(1000, (compiled.params or {}).values())
                    self.assertIn(0, (compiled.params or {}).values())
                    self.lessons.get_lesson.assert_not_awaited()

    async def test_search_escapes_wildcards_and_escape_character(self) -> None:
        for catalog, fields in SEARCH_FIELDS.items():
            with self.subTest(catalog=catalog):
                response = await self.request(catalog, {"q": "50%_/"})
                self.assertEqual(response.status_code, 200)
                compiled = self.compiled_query()
                for field in fields:
                    self.assertEqual((compiled.params or {})[f"{field}_1"], "50/%/_//")
                self.assertEqual(str(compiled).count("ESCAPE '/'"), len(fields))

    async def test_search_value_is_bound_not_interpolated(self) -> None:
        value = "' OR 1=1 --"
        for catalog in SEARCH_FIELDS:
            with self.subTest(catalog=catalog):
                response = await self.request(catalog, {"q": value})
                self.assertEqual(response.status_code, 200)
                compiled = self.compiled_query()
                self.assertNotIn(value, str(compiled))
                self.assertIn(value, (compiled.params or {}).values())

    async def test_search_length_is_validated(self) -> None:
        for catalog in SEARCH_FIELDS:
            with self.subTest(catalog=catalog):
                response = await self.request(catalog, {"q": "x" * 201})
                self.assertEqual(response.status_code, 422)
                self.execute.assert_not_awaited()
                response = await self.request(catalog, {"q": "x" * 200})
                self.assertEqual(response.status_code, 200)

    async def test_existing_filter_and_pagination_validation_is_preserved(self) -> None:
        for catalog in SEARCH_FIELDS:
            for params in (
                {"lesson_id": "not-a-uuid"},
                {"limit": "0"},
                {"limit": "5001"},
                {"offset": "-1"},
            ):
                with self.subTest(catalog=catalog, params=params):
                    response = await self.request(catalog, {"q": "horse", **params})
                    self.assertEqual(response.status_code, 422)
                    self.execute.assert_not_awaited()
