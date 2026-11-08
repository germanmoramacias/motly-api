"""Private application-data backup before a quiz schema change."""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import engine


async def backup(destination: Path) -> None:
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="REPEATABLE READ")
        async with connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            tables = (
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables "
                            "WHERE schemaname='public' ORDER BY tablename"
                        )
                    )
                )
                .scalars()
                .all()
            )
            quote = connection.dialect.identifier_preparer.quote_identifier
            data = {}
            for table in tables:
                data[table] = await connection.scalar(
                    text(
                        "SELECT coalesce(jsonb_agg(to_jsonb(row)), '[]'::jsonb) "
                        f"FROM public.{quote(table)} AS row"
                    )
                )
    payload = {
        "format": "motly-public-data-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "tables": data,
    }
    result = await asyncio.to_thread(write_backup, destination, payload)
    print(json.dumps(result))


def write_backup(destination: Path, payload: dict) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
        compressed.write(json.dumps(payload, ensure_ascii=False).encode())
    return {
        "backup": str(destination),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "row_counts": {name: len(rows) for name, rows in payload["tables"].items()},
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        await backup(args.output)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
