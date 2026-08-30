"""SQL and row mapping for contacts and the application_contacts join."""

from __future__ import annotations

import sqlite3

from .models import Contact


def add(conn: sqlite3.Connection, name: str, **fields: object) -> Contact:
    raise NotImplementedError


def list_(conn: sqlite3.Connection, company: str | None = None) -> list[Contact]:
    raise NotImplementedError


def link(
    conn: sqlite3.Connection,
    app_id: int,
    contact_id: int,
    relationship: str,
) -> None:
    raise NotImplementedError


def for_application(conn: sqlite3.Connection, app_id: int) -> list[tuple[Contact, str]]:
    raise NotImplementedError
