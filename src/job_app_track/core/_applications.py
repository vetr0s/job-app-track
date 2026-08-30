"""SQL and row mapping for applications and their status timeline.

record_status writes an event and updates applications.status in one
transaction; the two must never drift.
"""

from __future__ import annotations

import sqlite3

from .models import Application, ApplicationDetail, StatusEvent

_INSERT_FIELDS = (
    "status",
    "source",
    "resume_version",
    "interest",
    "applied_at",
    "notes",
)


def _application(row: sqlite3.Row) -> Application:
    return Application(**dict(row))


def _event(row: sqlite3.Row) -> StatusEvent:
    return StatusEvent(**dict(row))


def insert(conn: sqlite3.Connection, role_id: int, **fields: object) -> Application:
    unknown = fields.keys() - set(_INSERT_FIELDS)
    if unknown:
        raise ValueError(f"unknown application fields: {', '.join(sorted(unknown))}")
    columns = ["role_id", *fields]
    values = [role_id, *fields.values()]
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO applications ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    app = get(conn, cursor.lastrowid)
    assert app is not None
    return app


def get(conn: sqlite3.Connection, app_id: int) -> Application | None:
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    return _application(row) if row is not None else None


def list_(
    conn: sqlite3.Connection,
    status: str | None = None,
    company: str | None = None,
) -> list[Application]:
    conditions: list[str] = []
    values: list[object] = []
    if status is not None:
        conditions.append("a.status = ?")
        values.append(status)
    if company is not None:
        conditions.append("c.name = ?")
        values.append(company)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        "SELECT a.* FROM applications a "
        "JOIN roles r ON r.id = a.role_id "
        "JOIN companies c ON c.id = r.company_id"
        f"{where} ORDER BY a.updated_at DESC, a.id DESC",
        values,
    ).fetchall()
    return [_application(row) for row in rows]


def detail(conn: sqlite3.Connection, app_id: int) -> ApplicationDetail:
    from . import _companies, _contacts, _interviews

    app = get(conn, app_id)
    if app is None:
        raise ValueError(f"application {app_id} does not exist")
    role = _companies.get_role(conn, app.role_id)
    assert role is not None
    company = _companies.get_company(conn, role.company_id)
    assert company is not None
    return ApplicationDetail(
        application=app,
        role=role,
        company=company,
        timeline=timeline(conn, app_id),
        contacts=_contacts.for_application(conn, app_id),
        interviews=_interviews.list_(conn, app_id=app_id),
    )


def record_status(
    conn: sqlite3.Connection,
    app_id: int,
    status: str,
    note: str | None = None,
    occurred_at: str | None = None,
) -> Application:
    if get(conn, app_id) is None:
        raise ValueError(f"application {app_id} does not exist")
    if occurred_at is None:
        conn.execute(
            "INSERT INTO application_status_events (application_id, status, note) VALUES (?, ?, ?)",
            (app_id, status, note),
        )
    else:
        conn.execute(
            "INSERT INTO application_status_events "
            "(application_id, status, occurred_at, note) VALUES (?, ?, ?, ?)",
            (app_id, status, occurred_at, note),
        )
    latest = conn.execute(
        "SELECT status FROM application_status_events "
        "WHERE application_id = ? ORDER BY occurred_at DESC, id DESC LIMIT 1",
        (app_id,),
    ).fetchone()
    assert latest is not None
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (latest["status"], app_id),
    )
    app = get(conn, app_id)
    assert app is not None
    return app


def timeline(conn: sqlite3.Connection, app_id: int) -> list[StatusEvent]:
    rows = conn.execute(
        "SELECT * FROM application_status_events "
        "WHERE application_id = ? ORDER BY occurred_at, id",
        (app_id,),
    ).fetchall()
    return [_event(row) for row in rows]


def update_fields(conn: sqlite3.Connection, app_id: int, **fields: object) -> Application:
    """Patch a subset of columns (interest, notes, resume_version, ...)."""
    if not fields:
        app = get(conn, app_id)
        if app is None:
            raise ValueError(f"application {app_id} does not exist")
        return app
    allowed = {"interest", "notes", "resume_version"}
    if not set(fields) <= allowed:
        raise ValueError("unsupported application field")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    cursor = conn.execute(
        f"UPDATE applications SET {assignments}, updated_at = datetime('now') WHERE id = ?",
        [*fields.values(), app_id],
    )
    if cursor.rowcount == 0:
        raise ValueError(f"application {app_id} does not exist")
    app = get(conn, app_id)
    assert app is not None
    return app


def pipeline(conn: sqlite3.Connection) -> dict[str, list[Application]]:
    out: dict[str, list[Application]] = {}
    for app in list_(conn):
        out.setdefault(app.status, []).append(app)
    return out
