import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from arqonbus import cli

pytestmark = [pytest.mark.integration, pytest.mark.socket]


class _JSONHandler(BaseHTTPRequestHandler):
    routes = {
        "/status": {"status": "healthy", "service": "arqonbus"},
        "/version": {"service": "arqonbus", "version": "0.1.0"},
    }

    def do_GET(self):
        payload = self.routes.get(self.path)
        if payload is None:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')
            return

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


@contextmanager
def _json_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JSONHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_cli_status_fetches_live_http_json(capsys):
    with _json_server() as http_url:
        rc = cli.main(["status", "--http-url", http_url, "--timeout-seconds", "2"])
        assert rc == 0
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "healthy"
        assert output["service"] == "arqonbus"


def test_cli_version_fetches_live_http_json(capsys):
    with _json_server() as http_url:
        rc = cli.main(["version", "--http-url", http_url, "--timeout-seconds", "2"])
        assert rc == 0
        output = json.loads(capsys.readouterr().out)
        assert output["service"] == "arqonbus"
        assert output["version"] == "0.1.0"
