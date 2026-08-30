"""SQL and row mapping for companies and roles. Called only by Store."""

from __future__ import annotations

import sqlite3

from .models import Company, Role

_COMPANY_FIELDS = ("website", "notes")
_ROLE_FIELDS = (
    "title",
    "location",
    "arrangement",
    "comp_min",
    "comp_max",
    "url",
    "jd_text",
    "notes",
)


def _known(fields: dict[str, object], allowed: tuple[str, ...], kind: str) -> None:
    unknown = fields.keys() - set(allowed)
    if unknown:
        raise ValueError(f"unknown {kind} fields: {', '.join(sorted(unknown))}")


def _company(row: sqlite3.Row) -> Company:
    return Company(**dict(row))


def _role(row: sqlite3.Row) -> Role:
    return Role(**dict(row))


# Every Role carries its company name, so each read joins companies.
_ROLE_SELECT = (
    "SELECT roles.*, companies.name AS company "
    "FROM roles JOIN companies ON companies.id = roles.company_id"
)


def upsert_company(conn: sqlite3.Connection, name: str, **fields: object) -> Company:
    """Insert by name, or return the existing row. Used by add and by import."""
    _known(fields, _COMPANY_FIELDS, "company")
    columns = ["name", *fields]
    values = [name, *fields.values()]
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO companies ({', '.join(columns)}) VALUES ({placeholders}) "
        "ON CONFLICT(name) DO NOTHING",
        values,
    )
    company = get_company_by_name(conn, name)
    assert company is not None
    return company


def get_company_by_name(conn: sqlite3.Connection, name: str) -> Company | None:
    row = conn.execute("SELECT * FROM companies WHERE name = ?", (name,)).fetchone()
    return _company(row) if row is not None else None


def list_companies(conn: sqlite3.Connection) -> list[Company]:
    rows = conn.execute("SELECT * FROM companies ORDER BY name, id").fetchall()
    return [_company(row) for row in rows]


def add_role(conn: sqlite3.Connection, company_id: int, **fields: object) -> Role:
    _known(fields, _ROLE_FIELDS, "role")
    columns = ["company_id", *fields]
    values = [company_id, *fields.values()]
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO roles ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    role = get_role(conn, cursor.lastrowid)
    assert role is not None
    return role


def list_roles(conn: sqlite3.Connection, company_id: int | None = None) -> list[Role]:
    sql = _ROLE_SELECT
    params: tuple[object, ...] = ()
    if company_id is not None:
        sql += " WHERE roles.company_id = ?"
        params = (company_id,)
    sql += " ORDER BY roles.created_at, roles.id"
    return [_role(row) for row in conn.execute(sql, params)]


def get_role(conn: sqlite3.Connection, role_id: int | None) -> Role | None:
    if role_id is None:
        return None
    row = conn.execute(f"{_ROLE_SELECT} WHERE roles.id = ?", (role_id,)).fetchone()
    return _role(row) if row is not None else None


def get_company(conn: sqlite3.Connection, company_id: int) -> Company | None:
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    return _company(row) if row is not None else None
