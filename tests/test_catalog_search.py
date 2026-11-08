from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.compiler import Compiled

from app.core.routing import api_v1_router
from app.db.session import get_db_session
from app.modules.expressions.models import Expression
from app.modules.notes.router import get_current_db_user_id, get_lesson_service
from app.modules.notes.service import LessonService
from app.modules.vocabulary.models import Vocabulary

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
        self.result = MagicMock()
        self.result.scalars.return_value.all.return_value = []
        self.execute = AsyncMock(return_value=self.result)
        execute_patch = patch.object(self.session, "execute", self.execute)
        execute_patch.start()
        self.addCleanup(execute_patch.stop)
        self.scalar = AsyncMock(return_value=0)
        scalar_patch = patch.object(self.session, "scalar", self.scalar)
        scalar_patch.start()
        self.addCleanup(scalar_patch.stop)
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
        self.scalar.reset_mock()
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
                self.assertEqual(
                    response.json(),
                    {"items": [], "total": 0, "total_pages": 0, "limit": 25, "offset": 50},
                )
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
                self.scalar.assert_awaited_once()
                count = self.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
                count_sql = str(count)
                self.assertIn("count(*)", count_sql)
                self.assertNotIn("LIMIT", count_sql)
                self.assertNotIn("OFFSET", count_sql)
                self.assertNotIn("ORDER BY", count_sql)
                count_where = count_sql.split("WHERE ", 1)[1].rsplit(") AS", 1)[0].strip()
                self.assertEqual(count_where, where.strip())
                for key in ("user_id_1", "lesson_id_1", *(f"{field}_1" for field in fields)):
                    self.assertEqual((count.params or {})[key], params[key])

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
                self.scalar.assert_not_awaited()
                response = await self.request(catalog, {"q": "x" * 200})
                self.assertEqual(response.status_code, 200)

    async def test_existing_filter_and_pagination_validation_is_preserved(self) -> None:
        for catalog in SEARCH_FIELDS:
            for params in (
                {"lesson_id": "not-a-uuid"},
                {"limit": "0"},
                {"limit": "5001"},
                {"offset": "-1"},
                {"sort": "term"},
                {"sort": "created_at_desc; DROP TABLE users"},
            ):
                with self.subTest(catalog=catalog, params=params):
                    response = await self.request(catalog, {"q": "horse", **params})
                    self.assertEqual(response.status_code, 422)
                    self.execute.assert_not_awaited()
                    self.scalar.assert_not_awaited()

    async def test_sort_direction_and_id_tiebreaker(self) -> None:
        for catalog in SEARCH_FIELDS:
            for sort, direction in (("created_at_desc", "DESC"), ("created_at_asc", "ASC")):
                with self.subTest(catalog=catalog, sort=sort):
                    response = await self.request(catalog, {"sort": sort})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(
                        f"ORDER BY {catalog}.created_at {direction}, {catalog}.id {direction}",
                        str(self.compiled_query()),
                    )

    async def test_total_pages_and_out_of_range_offset(self) -> None:
        for catalog in SEARCH_FIELDS:
            for total, limit, offset, pages in (
                (0, 50, 0, 0),
                (1, 50, 0, 1),
                (50, 50, 0, 1),
                (51, 50, 0, 2),
                (51, 50, 50, 2),
                (51, 50, 100, 2),
            ):
                with self.subTest(catalog=catalog, total=total, limit=limit, offset=offset):
                    self.scalar.return_value = total
                    response = await self.request(
                        catalog, {"limit": str(limit), "offset": str(offset)}
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        response.json(),
                        {
                            "items": [],
                            "total": total,
                            "total_pages": pages,
                            "limit": limit,
                            "offset": offset,
                        },
                    )
                    self.assertNotIn("X-Total-Count", response.headers)

    async def test_alphabetical_sort_is_case_insensitive_before_pagination(self) -> None:
        for catalog, field in (("vocabulary", "term"), ("expressions", "text")):
            for suffix, direction in (("asc", "ASC"), ("desc", "DESC")):
                with self.subTest(catalog=catalog, direction=direction):
                    self.scalar.return_value = 51
                    response = await self.request(
                        catalog,
                        {
                            "sort": f"{field}_{suffix}",
                            "q": "word",
                            "lesson_id": str(LESSON_ID),
                            "limit": "6",
                            "offset": "12",
                        },
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["total"], 51)
                    self.assertEqual(response.json()["total_pages"], 9)
                    sql = str(self.compiled_query())
                    ordering = (
                        f"ORDER BY lower({catalog}.{field}) {direction}, {catalog}.id {direction}"
                    )
                    self.assertIn(ordering, sql)
                    self.assertLess(sql.index(ordering), sql.index("LIMIT"))
                    self.assertIn(f"{catalog}.user_id =", sql)
                    self.assertIn(f"{catalog}.lesson_id =", sql)
                    self.lessons.get_lesson.assert_awaited_once_with(
                        lesson_id=LESSON_ID, user_id=USER_ID
                    )
                    count = str(self.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
                    self.assertNotIn("ORDER BY", count)
                    self.assertNotIn("LIMIT", count)

    async def test_catalog_specific_sort_values_are_validated(self) -> None:
        for catalog, invalid in (("vocabulary", "text_asc"), ("expressions", "term_desc")):
            response = await self.request(catalog, {"sort": invalid})
            self.assertEqual(response.status_code, 422)
            self.execute.assert_not_awaited()
            self.scalar.assert_not_awaited()

    async def test_items_keep_their_existing_fields(self) -> None:
        now = datetime.now(UTC)
        item_id = UUID("00000000-0000-0000-0000-000000000003")
        common = {
            "id": item_id,
            "user_id": USER_ID,
            "lesson_id": None,
            "created_at": now,
            "updated_at": now,
        }
        entries = {
            "vocabulary": Vocabulary(
                **common, term="horse", definition="A large riding animal", example=None
            ),
            "expressions": Expression(
                **common,
                text="warm up",
                meaning="Prepare for exercise",
                keyword="warm",
                group=None,
                example=None,
            ),
        }
        for catalog, item in entries.items():
            with self.subTest(catalog=catalog):
                self.result.scalars.return_value.all.return_value = [item]
                self.scalar.return_value = 51
                response = await self.request(catalog, {"limit": "1", "offset": "50"})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["total"], 51)
                self.assertEqual(payload["total_pages"], 51)
                self.assertEqual(len(payload["items"]), 1)
                entry = payload["items"][0]
                self.assertEqual(entry["id"], str(item_id))
                self.assertEqual(entry["user_id"], str(USER_ID))
                self.assertIsNone(entry["lesson_id"])
                self.assertIsNone(entry["example"])
                self.assertIn("created_at", entry)
                self.assertIn("updated_at", entry)
                for field in SEARCH_FIELDS[catalog]:
                    self.assertIn(field, entry)
