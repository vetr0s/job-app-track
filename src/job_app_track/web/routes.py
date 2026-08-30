"""One handler per route, plus the ROUTES table dispatch() reads.

Handlers take a Request and return a Response. They read req.form, call one
Store method, and hand the frozen dataclasses to a template. A read handler
branches on req.is_htmx: page() for a navigation, fragment() for a swap. A
write handler returns the swapped fragment for an htmx caller and a redirect
for a plain form post; the matching read handler renders that fragment, so a
write ends by calling it.

enums feeds every <select>. Nothing here knows SQL.
"""

from __future__ import annotations

from importlib import resources

from ..core import enums
from ..importer import import_csv
from .http import Request, Response, Route
from .render import fragment, page

_STATIC_TYPES = {".css": "text/css", ".js": "text/javascript"}


# -- form reading ----------------------------------------------------------


def _str(form: dict[str, str], key: str) -> str | None:
    value = form.get(key, "").strip()
    return value or None


def _int(form: dict[str, str], key: str) -> int | None:
    raw = form.get(key, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{key} must be a whole number") from None


def _required_int(form: dict[str, str], key: str) -> int:
    value = _int(form, key)
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _required_str(form: dict[str, str], key: str) -> str:
    value = _str(form, key)
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _page(template: str, **ctx: object) -> Response:
    return page(template, enums=enums, **ctx)


def _fragment(template: str, **ctx: object) -> Response:
    return fragment(template, enums=enums, **ctx)


# -- pipeline and static -------------------------------------------------


def pipeline(req: Request) -> Response:
    board = req.store.pipeline()
    columns = [(status, board.get(status, [])) for status in enums.STATUSES]
    total = sum(len(apps) for _, apps in columns)
    template = "_board.html" if req.is_htmx else "pipeline.html"
    render = _fragment if req.is_htmx else _page
    return render(template, columns=columns, total=total)


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


# -- applications ------------------------------------------------------


def application_index(req: Request) -> Response:
    status = req.query.get("status") or None
    company = req.query.get("company") or None
    apps = req.store.applications(status=status, company=company)
    view = dict(apps=apps, status=status or "", company=company or "")
    if req.is_htmx:
        return _fragment("_applications.html", **view)
    return _page("applications.html", roles=req.store.roles(), **view)


def application_show(req: Request) -> Response:
    detail = req.store.application_detail(int(req.params["id"]))
    view = dict(d=detail, all_contacts=req.store.contacts())
    if req.is_htmx:
        return _fragment("_application.html", **view)
    return _page("application.html", **view)


def application_apply(req: Request) -> Response:
    req.store.apply(
        role_id=_required_int(req.form, "role_id"),
        source=_str(req.form, "source"),
        resume_version=_str(req.form, "resume_version"),
        interest=_str(req.form, "interest"),
        note=_str(req.form, "note"),
    )
    if req.is_htmx:
        return application_index(req)
    return Response.redirect("/applications")


def application_status(req: Request) -> Response:
    app_id = int(req.params["id"])
    req.store.record_status(
        app_id,
        _required_str(req.form, "status"),
        note=_str(req.form, "note"),
        occurred_at=_str(req.form, "at"),
    )
    if req.form.get("view") == "board":
        return pipeline(req)
    if req.is_htmx:
        return application_show(req)
    return Response.redirect(f"/applications/{app_id}")


def application_interest(req: Request) -> Response:
    app_id = int(req.params["id"])
    req.store.set_interest(app_id, _str(req.form, "interest"))
    if req.is_htmx:
        return application_show(req)
    return Response.redirect(f"/applications/{app_id}")


def application_note(req: Request) -> Response:
    app_id = int(req.params["id"])
    req.store.add_note(app_id, _required_str(req.form, "text"))
    if req.is_htmx:
        return application_show(req)
    return Response.redirect(f"/applications/{app_id}")


def contact_link(req: Request) -> Response:
    app_id = int(req.params["id"])
    req.store.link_contact(
        app_id,
        contact_id=_required_int(req.form, "contact_id"),
        relationship=_required_str(req.form, "relationship"),
    )
    if req.is_htmx:
        return application_show(req)
    return Response.redirect(f"/applications/{app_id}")


# -- companies -------------------------------------------------------


def company_index(req: Request) -> Response:
    companies = req.store.companies()
    if req.is_htmx:
        return _fragment("_companies.html", companies=companies)
    return _page("companies.html", companies=companies)


def company_create(req: Request) -> Response:
    req.store.add_company(
        _required_str(req.form, "name"),
        website=_str(req.form, "website"),
        notes=_str(req.form, "notes"),
    )
    if req.is_htmx:
        return company_index(req)
    return Response.redirect("/companies")


# -- roles ---------------------------------------------------------


def role_index(req: Request) -> Response:
    company = req.query.get("company") or None
    roles = req.store.roles(company=company)
    view = dict(roles=roles, company=company or "")
    if req.is_htmx:
        return _fragment("_roles.html", **view)
    return _page("roles.html", companies=req.store.companies(), **view)


def role_create(req: Request) -> Response:
    req.store.add_role(
        company=_required_str(req.form, "company"),
        title=_required_str(req.form, "title"),
        location=_str(req.form, "location"),
        arrangement=_str(req.form, "arrangement"),
        comp_min=_int(req.form, "comp_min"),
        comp_max=_int(req.form, "comp_max"),
        url=_str(req.form, "url"),
        notes=_str(req.form, "notes"),
    )
    if req.is_htmx:
        return role_index(req)
    return Response.redirect("/roles")


# -- contacts ---------------------------------------------------------


def contact_index(req: Request) -> Response:
    company = req.query.get("company") or None
    contacts = req.store.contacts(company=company)
    view = dict(contacts=contacts, company=company or "")
    if req.is_htmx:
        return _fragment("_contacts.html", **view)
    return _page("contacts.html", companies=req.store.companies(), **view)


def contact_create(req: Request) -> Response:
    req.store.add_contact(
        _required_str(req.form, "name"),
        company=_str(req.form, "company"),
        title=_str(req.form, "title"),
        email=_str(req.form, "email"),
        phone=_str(req.form, "phone"),
        linkedin=_str(req.form, "linkedin"),
        notes=_str(req.form, "notes"),
    )
    if req.is_htmx:
        return contact_index(req)
    return Response.redirect("/contacts")


# -- interviews ---------------------------------------------------------


def interview_index(req: Request) -> Response:
    app_id = _int(req.query, "app")
    upcoming = req.query.get("upcoming") == "1"
    interviews = req.store.interviews(app_id=app_id, upcoming=upcoming)
    view = dict(interviews=interviews, app=app_id or "", upcoming=upcoming)
    if req.is_htmx:
        return _fragment("_interviews.html", **view)
    return _page(
        "interviews.html",
        applications=req.store.applications(),
        contacts=req.store.contacts(),
        **view,
    )


def interview_create(req: Request) -> Response:
    req.store.add_interview(
        _required_int(req.form, "app_id"),
        kind=_required_str(req.form, "kind"),
        scheduled_at=_str(req.form, "scheduled_at"),
        duration_min=_int(req.form, "duration_min"),
        location=_str(req.form, "location"),
        contact_id=_int(req.form, "contact_id"),
        prep_notes=_str(req.form, "prep_notes"),
    )
    if req.is_htmx:
        return interview_index(req)
    return Response.redirect("/interviews")


def interview_outcome(req: Request) -> Response:
    req.store.set_interview_outcome(
        int(req.params["id"]),
        _required_str(req.form, "outcome"),
        debrief_notes=_str(req.form, "debrief_notes"),
    )
    if req.is_htmx:
        return interview_index(req)
    return Response.redirect("/interviews")


# -- import ---------------------------------------------------------


def import_view(req: Request) -> Response:
    return _page("import.html")


def import_run(req: Request) -> Response:
    path = _required_str(req.form, "csv_path")
    force = req.form.get("force") == "1"
    try:
        count = import_csv(req.store, path, force=force)
    except FileNotFoundError:
        raise ValueError(f"cannot read {path}: no such file") from None
    return _page("import.html", imported=count)


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
