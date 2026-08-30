"""SQL and row mapping for companies and roles. Called only by Store."""

from __future__ import annotations

import sqlite3

from .models import Company, Role


def upsert_company(conn: sqlite3.Connection, name: str, **fields: object) -> Company:
    """Insert by name, or return the existing row. Used by add and by import."""
    raise NotImplementedError


def get_company_by_name(conn: sqlite3.Connection, name: str) -> Company | None:
    raise NotImplementedError


def list_companies(conn: sqlite3.Connection) -> list[Company]:
    raise NotImplementedError


def add_role(conn: sqlite3.Connection, company_id: int, **fields: object) -> Role:
    raise NotImplementedError


def list_roles(conn: sqlite3.Connection, company_id: int | None = None) -> list[Role]:
    raise NotImplementedError


def get_role_by_title(conn: sqlite3.Connection, company_id: int, title: str) -> Role | None:
    raise NotImplementedError
