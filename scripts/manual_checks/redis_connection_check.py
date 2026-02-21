#!/usr/bin/env python3
"""Validate Valkey/Redis connectivity for ArqonBus."""

from __future__ import annotations

import asyncio
import os
import sys


def _resolve_redis_url() -> str | None:
    return os.getenv("ARQONBUS_VALKEY_URL") or os.getenv("ARQONBUS_REDIS_URL")


async def _run() -> int:
    redis_url = _resolve_redis_url()
    if not redis_url:
        print("ERROR: set ARQONBUS_VALKEY_URL (or ARQONBUS_REDIS_URL)")
        return 2

    try:
        import redis.asyncio as redis
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: redis dependency unavailable: {exc}")
        return 2

    client = redis.from_url(redis_url, decode_responses=True)
    try:
        pong = await client.ping()
        if pong is True:
            print(f"OK: Valkey/Redis reachable at {redis_url}")
            return 0
        print(f"ERROR: ping returned unexpected response: {pong!r}")
        return 1
    except Exception as exc:
        print(f"ERROR: unable to reach Valkey/Redis at {redis_url}: {exc}")
        return 1
    finally:
        await client.aclose()


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
