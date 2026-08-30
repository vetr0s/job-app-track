"""http.server glue. Builds a Request-shaped call into dispatch() and writes
the Response back. Single-threaded on purpose: one SQLite connection, requests
served one at a time. Fine for one user on a private network.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

from ..core import Store
from .http import dispatch
from .routes import ROUTES


class _Server(HTTPServer):
    def __init__(self, address: tuple[str, int], store: Store) -> None:
        super().__init__(address, _Handler)
        self.store = store


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    # HTTP/1.0 so every connection closes after one response. The server is
    # single-threaded; an HTTP/1.1 keep-alive socket left idle by a browser
    # would block accept() for every other connection and wedge it.
    protocol_version = "HTTP/1.0"

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def _handle(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        response = dispatch(
            ROUTES,
            method,
            self.path,
            body=body,
            headers=self.headers,
            store=self.server.store,
        )
        payload = response.body.encode("utf-8")
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        # One tidy line per request instead of the noisy default.
        print(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}".rstrip())


def make_server(host: str, port: int, store: Store) -> _Server:
    return _Server((host, port), store)
