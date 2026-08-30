"""SQL and row mapping for applications and their status timeline.

record_status writes an event and updates applications.status in one
transaction; the two must never drift.
"""

from __future__ import annotations

import sqlite3

from .models import Application, ApplicationDetail, StatusEvent


def insert(conn: sqlite3.Connection, role_id: int, **fields: object) -> Application:
    raise NotImplementedError


def get(conn: sqlite3.Connection, app_id: int) -> Application | None:
    raise NotImplementedError


def list_(
    conn: sqlite3.Connection,
    status: str | None = None,
    company: str | None = None,
) -> list[Application]:
    raise NotImplementedError


def detail(conn: sqlite3.Connection, app_id: int) -> ApplicationDetail:
    raise NotImplementedError


def record_status(
    conn: sqlite3.Connection,
    app_id: int,
    status: str,
    note: str | None = None,
    occurred_at: str | None = None,
) -> Application:
    raise NotImplementedError


def timeline(conn: sqlite3.Connection, app_id: int) -> list[StatusEvent]:
    raise NotImplementedError


def update_fields(conn: sqlite3.Connection, app_id: int, **fields: object) -> Application:
    """Patch a subset of columns (interest, notes, resume_version, ...)."""
    raise NotImplementedError


def pipeline(conn: sqlite3.Connection) -> dict[str, list[Application]]:
    raise NotImplementedError
