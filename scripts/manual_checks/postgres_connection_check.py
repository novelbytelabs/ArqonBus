#!/usr/bin/env python3
"""Validate Postgres connectivity for ArqonBus."""

from __future__ import annotations

import asyncio
import os
import sys


def _resolve_postgres_url() -> str | None:
    return os.getenv("ARQONBUS_POSTGRES_URL")


async def _run() -> int:
    postgres_url = _resolve_postgres_url()
    if not postgres_url:
        print("ERROR: set ARQONBUS_POSTGRES_URL")
        return 2

    try:
        import asyncpg
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: asyncpg dependency unavailable: {exc}")
        return 2

    conn = None
    try:
        conn = await asyncpg.connect(postgres_url)
        value = await conn.fetchval("SELECT 1")
        if value == 1:
            print(f"OK: Postgres reachable at {postgres_url}")
            return 0
        print(f"ERROR: unexpected probe result: {value!r}")
        return 1
    except Exception as exc:
        print(f"ERROR: unable to reach Postgres at {postgres_url}: {exc}")
        return 1
    finally:
        if conn is not None:
            await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
