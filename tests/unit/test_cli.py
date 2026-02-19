import json

import pytest

from arqonbus import cli


def test_parse_header_items_accepts_multiple_headers():
    headers = cli._parse_header_items(["X-Tenant:tenant-a", "X-Trace:abc123"])
    assert headers == {"X-Tenant": "tenant-a", "X-Trace": "abc123"}


def test_parse_header_items_rejects_invalid_format():
    with pytest.raises(ValueError, match="Invalid header format"):
        cli._parse_header_items(["not-a-header"])


def test_status_command_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_http_get_json",
        lambda url, timeout_seconds: {"status": "healthy", "url": url, "timeout": timeout_seconds},
    )
    rc = cli.main(["status", "--http-url", "http://localhost:9999", "--timeout-seconds", "2"])
    assert rc == 0

    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed["status"] == "healthy"
    assert parsed["url"] == "http://localhost:9999/status"


def test_tail_command_reports_header_parse_error(capsys):
    rc = cli.main(["tail", "--header", "bad-header"])
    assert rc == 1
    assert "Invalid header format" in capsys.readouterr().err
