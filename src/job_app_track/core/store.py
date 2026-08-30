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
        self._savepoint_id = 0

    @classmethod
    def open(cls, db_path: str | Path | None = None) -> Store:
        """Resolve the path, connect, migrate to head, return a Store."""
        path = Path(db_path) if db_path is not None else db.default_db_path()
        conn = db.connect(path)
        try:
            db.migrate(conn)
        except BaseException:
            conn.close()
            raise
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
        self._savepoint_id += 1
        name = f"jat_{self._savepoint_id}"
        self._conn.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            self._conn.execute(f"ROLLBACK TO {name}")
            self._conn.execute(f"RELEASE {name}")
            raise
        else:
            self._conn.execute(f"RELEASE {name}")

    # -- companies and roles ------------------------------------------------

    def add_company(self, name: str, **fields: object) -> Company:
        with self.tx():
            return _companies.upsert_company(self._conn, name, **fields)

    def companies(self) -> list[Company]:
        return _companies.list_companies(self._conn)

    def add_role(self, *, company: str, title: str, **fields: object) -> Role:
        with self.tx():
            owner = _companies.upsert_company(self._conn, company)
            return _companies.add_role(self._conn, owner.id, title=title, **fields)

    def roles(self, *, company: str | None = None) -> list[Role]:
        company_id = None
        if company is not None:
            owner = _companies.get_company_by_name(self._conn, company)
            if owner is None:
                return []
            company_id = owner.id
        return _companies.list_roles(self._conn, company_id)

    # -- applications -----------------------------------------------------

    def apply(
        self,
        *,
        role_id: int,
        source: str | None = None,
        resume_version: str | None = None,
        interest: str | None = None,
        note: str | None = None,
        status: str = "applied",
        applied_at: str | None = None,
        notes: str | None = None,
        occurred_at: str | None = None,
    ) -> Application:
        with self.tx():
            if _companies.get_role(self._conn, role_id) is None:
                raise ValueError(f"role {role_id} does not exist")
            app = _applications.insert(
                self._conn,
                role_id,
                status=status,
                source=source,
                resume_version=resume_version,
                interest=interest,
                applied_at=applied_at,
                notes=notes,
            )
            return _applications.record_status(
                self._conn,
                app.id,
                status,
                note=note,
                occurred_at=occurred_at,
            )

    def applications(
        self,
        *,
        status: str | None = None,
        company: str | None = None,
    ) -> list[Application]:
        return _applications.list_(self._conn, status, company)

    def application_detail(self, app_id: int) -> ApplicationDetail:
        return _applications.detail(self._conn, app_id)

    def record_status(
        self,
        app_id: int,
        status: str,
        *,
        note: str | None = None,
        occurred_at: str | None = None,
    ) -> Application:
        with self.tx():
            return _applications.record_status(self._conn, app_id, status, note, occurred_at)

    def set_interest(self, app_id: int, interest: str | None) -> Application:
        with self.tx():
            return _applications.update_fields(self._conn, app_id, interest=interest)

    def add_note(self, app_id: int, text: str) -> Application:
        with self.tx():
            current = _applications.get(self._conn, app_id)
            if current is None:
                raise ValueError(f"application {app_id} does not exist")
            notes = f"{current.notes}\n{text}" if current.notes else text
            return _applications.update_fields(self._conn, app_id, notes=notes)

    def pipeline(self) -> dict[str, list[Application]]:
        return _applications.pipeline(self._conn)

    # -- contacts --------------------------------------------------------

    def add_contact(self, name: str, *, company: str | None = None, **fields: object) -> Contact:
        with self.tx():
            company_id = None
            if company is not None:
                company_id = _companies.upsert_company(self._conn, company).id
            return _contacts.add(self._conn, name, company_id=company_id, **fields)

    def contacts(self, *, company: str | None = None) -> list[Contact]:
        return _contacts.list_(self._conn, company)

    def link_contact(self, app_id: int, *, contact_id: int, relationship: str) -> None:
        with self.tx():
            _contacts.link(self._conn, app_id, contact_id, relationship)

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
        with self.tx():
            return _interviews.add(
                self._conn,
                app_id,
                kind,
                scheduled_at=scheduled_at,
                duration_min=duration_min,
                location=location,
                contact_id=contact_id,
                prep_notes=prep_notes,
            )

    def set_interview_outcome(
        self,
        interview_id: int,
        outcome: str,
        *,
        debrief_notes: str | None = None,
    ) -> Interview:
        with self.tx():
            return _interviews.set_outcome(self._conn, interview_id, outcome, debrief_notes)

    def interviews(
        self,
        *,
        app_id: int | None = None,
        upcoming: bool = False,
    ) -> list[Interview]:
        return _interviews.list_(self._conn, app_id, upcoming)


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
