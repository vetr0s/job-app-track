"""One handler per route, plus the ROUTES table dispatch() reads.

Handlers take a Request and return a Response. They call Store methods and hand
the frozen dataclasses to a template. A read handler that an htmx request hit
should return fragment(); a write handler should return the swapped fragment or
a redirect. enums feeds the <select> options.

pipeline and static are implemented as the worked examples. Every other handler
returns 501 until it is filled in; see docs/web-frontend-plan.html.
"""

from __future__ import annotations

from importlib import resources

from ..core import enums
from .http import Request, Response, Route
from .render import fragment, page

_STATIC_TYPES = {".css": "text/css", ".js": "text/javascript"}


def _todo(req: Request) -> Response:
    return Response.text(f"{req.method} {req.path} is not implemented yet", 501)


# -- implemented --------------------------------------------------------------


def pipeline(req: Request) -> Response:
    board = req.store.pipeline()
    ordered = [(status, board.get(status, [])) for status in enums.STATUSES]
    total = sum(len(apps) for _, apps in ordered)
    template = "_board.html" if req.is_htmx else "pipeline.html"
    render = fragment if req.is_htmx else page
    return render(template, columns=ordered, total=total)


def static(req: Request) -> Response:
    name = req.params["name"]
    if "/" in name or name.startswith("."):
        raise LookupError("not found")
    files = resources.files("job_app_track.web.static")
    target = files / name
    if not target.is_file():
        raise LookupError(f"no such asset: {name}")
    suffix = name[name.rfind(".") :]
    body = target.read_text("utf-8")
    return Response(body, 200, {"Content-Type": _STATIC_TYPES.get(suffix, "text/plain")})


# -- stubs: fill these in against the plan ----------------------------------

application_index = _todo
application_show = _todo
application_apply = _todo
application_status = _todo
application_interest = _todo
application_note = _todo
company_index = _todo
company_create = _todo
role_index = _todo
role_create = _todo
contact_index = _todo
contact_create = _todo
contact_link = _todo
interview_index = _todo
interview_create = _todo
interview_outcome = _todo
import_view = _todo
import_run = _todo


ROUTES: list[Route] = [
    Route("GET", "/", pipeline),
    Route("GET", "/static/<str:name>", static),
    Route("GET", "/applications", application_index),
    Route("GET", "/applications/<int:id>", application_show),
    Route("POST", "/applications", application_apply),
    Route("POST", "/applications/<int:id>/status", application_status),
    Route("POST", "/applications/<int:id>/interest", application_interest),
    Route("POST", "/applications/<int:id>/note", application_note),
    Route("POST", "/applications/<int:id>/contacts", contact_link),
    Route("GET", "/companies", company_index),
    Route("POST", "/companies", company_create),
    Route("GET", "/roles", role_index),
    Route("POST", "/roles", role_create),
    Route("GET", "/contacts", contact_index),
    Route("POST", "/contacts", contact_create),
    Route("GET", "/interviews", interview_index),
    Route("POST", "/interviews", interview_create),
    Route("POST", "/interviews/<int:id>/outcome", interview_outcome),
    Route("GET", "/import", import_view),
    Route("POST", "/import", import_run),
]
