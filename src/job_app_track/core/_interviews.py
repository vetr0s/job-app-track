"""SQL and row mapping for interviews. Called only by Store."""

from __future__ import annotations

import sqlite3

from .models import Interview


def add(conn: sqlite3.Connection, app_id: int, kind: str, **fields: object) -> Interview:
    raise NotImplementedError


def set_outcome(
    conn: sqlite3.Connection,
    interview_id: int,
    outcome: str,
    debrief_notes: str | None = None,
) -> Interview:
    raise NotImplementedError


def list_(
    conn: sqlite3.Connection,
    app_id: int | None = None,
    upcoming: bool = False,
) -> list[Interview]:
    raise NotImplementedError
