"""Store: the single seam between a frontend and the database.

A frontend parses input, calls one Store method, and formats the result. It
never sees SQL or a connection. Each concern's SQL lives in a _module that
Store composes; tx() groups several writes into one atomic unit.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import _applications, _companies, _contacts, _interviews, db
from .models import (
    Application,
    ApplicationDetail,
    Company,
    Contact,
    Interview,
    Role,
    StatusEvent,
)


class Store:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @classmethod
    def open(cls, db_path: str | Path | None = None) -> Store:
        """Resolve the path, connect, migrate to head, return a Store."""
        path = Path(db_path) if db_path is not None else db.default_db_path()
        conn = db.connect(path)
        db.migrate(conn)
        return cls(conn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def tx(self) -> Iterator[None]:
        """Run the block in one transaction; roll back on any exception."""
        with self._conn:
            yield

    # -- companies and roles ------------------------------------------------

    def add_company(self, name: str, **fields: object) -> Company:
        raise NotImplementedError

    def companies(self) -> list[Company]:
        raise NotImplementedError

    def add_role(self, *, company: str, title: str, **fields: object) -> Role:
        raise NotImplementedError

    def roles(self, *, company: str | None = None) -> list[Role]:
        raise NotImplementedError

    # -- applications -----------------------------------------------------

    def apply(
        self,
        *,
        company: str,
        role: str,
        source: str | None = None,
        resume_version: str | None = None,
        interest: str | None = None,
        note: str | None = None,
    ) -> Application:
        raise NotImplementedError

    def applications(
        self,
        *,
        status: str | None = None,
        company: str | None = None,
    ) -> list[Application]:
        raise NotImplementedError

    def application_detail(self, app_id: int) -> ApplicationDetail:
        raise NotImplementedError

    def record_status(
        self,
        app_id: int,
        status: str,
        *,
        note: str | None = None,
        occurred_at: str | None = None,
    ) -> Application:
        raise NotImplementedError

    def set_interest(self, app_id: int, interest: str | None) -> Application:
        raise NotImplementedError

    def add_note(self, app_id: int, text: str) -> Application:
        raise NotImplementedError

    def pipeline(self) -> dict[str, list[Application]]:
        raise NotImplementedError

    # -- contacts --------------------------------------------------------

    def add_contact(self, name: str, *, company: str | None = None, **fields: object) -> Contact:
        raise NotImplementedError

    def contacts(self, *, company: str | None = None) -> list[Contact]:
        raise NotImplementedError

    def link_contact(self, app_id: int, *, contact_id: int, relationship: str) -> None:
        raise NotImplementedError

    # -- interviews ----------------------------------------------------

    def add_interview(
        self,
        app_id: int,
        *,
        kind: str,
        scheduled_at: str | None = None,
        duration_min: int | None = None,
        location: str | None = None,
        contact_id: int | None = None,
        prep_notes: str | None = None,
    ) -> Interview:
        raise NotImplementedError

    def set_interview_outcome(
        self,
        interview_id: int,
        outcome: str,
        *,
        debrief_notes: str | None = None,
    ) -> Interview:
        raise NotImplementedError

    def interviews(
        self,
        *,
        app_id: int | None = None,
        upcoming: bool = False,
    ) -> list[Interview]:
        raise NotImplementedError


__all__ = [
    "Store",
    "Application",
    "ApplicationDetail",
    "Company",
    "Contact",
    "Interview",
    "Role",
    "StatusEvent",
]
