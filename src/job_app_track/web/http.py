"""Transport primitives for the web frontend. No domain knowledge lives here.

A Route binds a method and a path pattern to a handler. dispatch() matches an
incoming request against the table, builds a Request, and turns the handler's
return value or exception into a Response. routes.py supplies the handlers and
the table; server.py feeds raw request data in and writes the Response out.
"""

from __future__ import annotations

import html
import re
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qs

from ..core import Store
from ..importer import ImportBlocked

_PARAM = re.compile(r"<(int|str):([a-z_]+)>")


@dataclass(frozen=True, slots=True)
class Request:
    method: str
    path: str
    params: dict[str, str]          # captured from the path pattern
    query: dict[str, str]           # first value wins
    form: dict[str, str]            # parsed x-www-form-urlencoded body
    headers: Mapping[str, str]
    store: Store

    @property
    def is_htmx(self) -> bool:
        return self.headers.get("HX-Request") == "true"


@dataclass(frozen=True, slots=True)
class Response:
    body: str = ""
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def html(cls, body: str, status: int = 200) -> Response:
        return cls(body, status, {"Content-Type": "text/html; charset=utf-8"})

    @classmethod
    def redirect(cls, location: str) -> Response:
        return cls("", 303, {"Location": location})

    @classmethod
    def text(cls, body: str, status: int) -> Response:
        return cls(body, status, {"Content-Type": "text/plain; charset=utf-8"})


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    pattern: str
    handler: Callable[[Request], Response]

    def regex(self) -> re.Pattern[str]:
        def sub(m: re.Match[str]) -> str:
            kind, name = m.groups()
            klass = r"\d+" if kind == "int" else r"[^/]+"
            return rf"(?P<{name}>{klass})"

        return re.compile("^" + _PARAM.sub(sub, self.pattern) + "$")


def dispatch(
    routes: list[Route],
    method: str,
    raw_path: str,
    *,
    body: bytes,
    headers: Mapping[str, str],
    store: Store,
) -> Response:
    """Match method+path to a route and run its handler.

    No route for the path is 404. A route for the path but not the method is
    405. A handler raising ValueError is 400, LookupError is 404, ImportBlocked
    is 409; each renders its message. An htmx caller gets that message wrapped
    in a small fragment so it lands in the page. Any other exception propagates
    so the server logs a traceback and returns 500.
    """
    path, _, query_string = raw_path.partition("?")
    path_matched = False
    for route in routes:
        match = route.regex().match(path)
        if match is None:
            continue
        path_matched = True
        if route.method != method:
            continue
        request = Request(
            method=method,
            path=path,
            params=match.groupdict(),
            query={k: v[0] for k, v in parse_qs(query_string).items()},
            form={k: v[0] for k, v in parse_qs(body.decode("utf-8")).items()},
            headers=headers,
            store=store,
        )
        try:
            return route.handler(request)
        except ValueError as exc:
            return _fail(request, str(exc), 400)
        except LookupError as exc:
            return _fail(request, str(exc), 404)
        except ImportBlocked as exc:
            return _fail(request, str(exc), 409)
        except sqlite3.IntegrityError as exc:
            return _fail(request, f"database rejected the change: {exc}", 400)
    if path_matched:
        return Response.text(f"method {method} not allowed", 405)
    return Response.text("not found", 404)


def _fail(request: Request, message: str, status: int) -> Response:
    """A user error: plain text for a navigation, an alert fragment for htmx."""
    if request.is_htmx:
        return Response.html(f'<p class="error" role="alert">{html.escape(message)}</p>', status)
    return Response.text(message, status)
