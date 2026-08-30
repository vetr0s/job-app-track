"""Jinja2 setup and the two helpers routes.py uses to build a Response.

page() renders a full document that extends base.html. fragment() renders a
partial for an htmx swap, with no surrounding chrome. Templates live in
templates/ and are packaged with the wheel.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from .http import Response

env = Environment(
    loader=PackageLoader("job_app_track.web", "templates"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def page(template: str, *, status: int = 200, **ctx: object) -> Response:
    return Response.html(env.get_template(template).render(**ctx), status)


def fragment(template: str, *, status: int = 200, **ctx: object) -> Response:
    return Response.html(env.get_template(template).render(**ctx), status)
