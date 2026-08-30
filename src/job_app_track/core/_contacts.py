"""SQL and row mapping for contacts and the application_contacts join."""

from __future__ import annotations

import sqlite3

from .models import Contact


_FIELDS = ("company_id", "title", "email", "phone", "linkedin", "notes")


def _contact(row: sqlite3.Row) -> Contact:
    return Contact(**{field: row[field] for field in Contact.__dataclass_fields__})


def _require_row(conn: sqlite3.Connection, table: str, row_id: int) -> None:
    row = conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table.removesuffix('s')} {row_id} not found")


def add(conn: sqlite3.Connection, name: str, **fields: object) -> Contact:
    values = {field: fields[field] for field in _FIELDS if field in fields}
    unknown = fields.keys() - values.keys()
    if unknown:
        raise ValueError(f"unknown contact fields: {', '.join(sorted(unknown))}")
    if values.get("company_id") is not None:
        _require_row(conn, "companies", int(values["company_id"]))

    columns = ["name", *values]
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO contacts ({', '.join(columns)}) VALUES ({placeholders})",
        [name, *values.values()],
    )
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    assert row is not None
    return _contact(row)


def list_(conn: sqlite3.Connection, company: str | None = None) -> list[Contact]:
    sql = "SELECT contacts.* FROM contacts"
    params: tuple[object, ...] = ()
    if company is not None:
        sql += " JOIN companies ON companies.id = contacts.company_id WHERE companies.name = ?"
        params = (company,)
    sql += " ORDER BY contacts.name COLLATE NOCASE, contacts.id"
    return [_contact(row) for row in conn.execute(sql, params)]


def link(
    conn: sqlite3.Connection,
    app_id: int,
    contact_id: int,
    relationship: str,
) -> None:
    _require_row(conn, "applications", app_id)
    _require_row(conn, "contacts", contact_id)
    conn.execute(
        "INSERT INTO application_contacts (application_id, contact_id, relationship) "
        "VALUES (?, ?, ?)",
        (app_id, contact_id, relationship),
    )


def for_application(conn: sqlite3.Connection, app_id: int) -> list[tuple[Contact, str]]:
    _require_row(conn, "applications", app_id)
    rows = conn.execute(
        "SELECT contacts.*, application_contacts.relationship "
        "FROM application_contacts "
        "JOIN contacts ON contacts.id = application_contacts.contact_id "
        "WHERE application_contacts.application_id = ? "
        "ORDER BY contacts.name COLLATE NOCASE, contacts.id, application_contacts.relationship",
        (app_id,),
    )
    return [(_contact(row), row["relationship"]) for row in rows]
