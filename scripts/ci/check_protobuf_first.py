#!/usr/bin/env python3
"""Fail CI if protobuf-first infrastructure guardrails are violated."""
from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _assert_absent(content: str, pattern: str, file_ref: str, failures: list[str]) -> None:
    if re.search(pattern, content, flags=re.MULTILINE):
        failures.append(f"{file_ref}: forbidden pattern `{pattern}` found")


def _assert_present(content: str, pattern: str, file_ref: str, failures: list[str]) -> None:
    if not re.search(pattern, content, flags=re.MULTILINE):
        failures.append(f"{file_ref}: required pattern `{pattern}` missing")


def main() -> int:
    failures: list[str] = []

    ws_file = "src/arqonbus/transport/websocket_bus.py"
    ws_content = _read(ws_file)
    _assert_absent(
        ws_content,
        r"EnvelopeValidator\.validate_and_parse_json\(",
        ws_file,
        failures,
    )
    _assert_present(
        ws_content,
        r"EnvelopeValidator\.validate_and_parse_wire\(",
        ws_file,
        failures,
    )
    _assert_present(
        ws_content,
        r"def _send_envelope_wire\(",
        ws_file,
        failures,
    )

    cfg_file = "src/arqonbus/config/config.py"
    cfg_content = _read(cfg_file)
    _assert_present(cfg_content, r"ARQONBUS_INFRA_PROTOCOL", cfg_file, failures)
    _assert_present(cfg_content, r"ARQONBUS_ALLOW_JSON_INFRA", cfg_file, failures)
    _assert_present(
        cfg_content,
        r"Infrastructure protocol must be protobuf in staging/prod",
        cfg_file,
        failures,
    )

    pg_file = "src/arqonbus/storage/postgres.py"
    pg_content = _read(pg_file)
    _assert_present(pg_content, r"envelope_proto", pg_file, failures)
    _assert_present(pg_content, r"envelope_to_proto_bytes", pg_file, failures)

    redis_file = "src/arqonbus/storage/redis_streams.py"
    redis_content = _read(redis_file)
    _assert_present(redis_content, r"envelope_proto_b64", redis_file, failures)
    _assert_present(redis_content, r"envelope_to_proto_bytes", redis_file, failures)

    if failures:
        print("protobuf-first infrastructure checks failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("protobuf-first infrastructure checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
