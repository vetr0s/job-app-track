"""SQL and row mapping for interviews. Called only by Store."""

from __future__ import annotations

import sqlite3

from .models import Interview


_FIELDS = ("scheduled_at", "duration_min", "location", "contact_id", "prep_notes")


def _interview(row: sqlite3.Row) -> Interview:
    return Interview(**{field: row[field] for field in Interview.__dataclass_fields__})


def _require_row(conn: sqlite3.Connection, table: str, row_id: int) -> None:
    row = conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table.removesuffix('s')} {row_id} not found")


def add(conn: sqlite3.Connection, app_id: int, kind: str, **fields: object) -> Interview:
    values = {field: fields[field] for field in _FIELDS if field in fields}
    unknown = fields.keys() - values.keys()
    if unknown:
        raise ValueError(f"unknown interview fields: {', '.join(sorted(unknown))}")
    _require_row(conn, "applications", app_id)
    if values.get("contact_id") is not None:
        _require_row(conn, "contacts", int(values["contact_id"]))

    columns = ["application_id", "kind", *values]
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO interviews ({', '.join(columns)}) VALUES ({placeholders})",
        [app_id, kind, *values.values()],
    )
    row = conn.execute("SELECT * FROM interviews WHERE id = ?", (cursor.lastrowid,)).fetchone()
    assert row is not None
    return _interview(row)


def set_outcome(
    conn: sqlite3.Connection,
    interview_id: int,
    outcome: str,
    debrief_notes: str | None = None,
) -> Interview:
    cursor = conn.execute(
        "UPDATE interviews SET outcome = ?, debrief_notes = ? WHERE id = ?",
        (outcome, debrief_notes, interview_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"interview {interview_id} not found")
    row = conn.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
    assert row is not None
    return _interview(row)


def list_(
    conn: sqlite3.Connection,
    app_id: int | None = None,
    upcoming: bool = False,
) -> list[Interview]:
    clauses: list[str] = []
    params: list[object] = []
    if app_id is not None:
        _require_row(conn, "applications", app_id)
        clauses.append("application_id = ?")
        params.append(app_id)
    if upcoming:
        clauses.extend(("scheduled_at >= datetime('now')", "outcome = 'pending'"))

    sql = "SELECT * FROM interviews"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY scheduled_at IS NULL, scheduled_at, id"
    return [_interview(row) for row in conn.execute(sql, params)]
