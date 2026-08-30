"""Command-line frontend for the job application store."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from . import format, importer
from .core import Store
from .core import db, enums


class _Parser(argparse.ArgumentParser):
    """Print full help, not just the usage line, on invalid use.

    Subparsers inherit this class, so the help shown is the one for the
    command that actually failed.
    """

    def error(self, message: str) -> None:
        self.print_help(sys.stderr)
        self.exit(2, f"\n{self.prog}: error: {message}\n")


def _read_parser(sub: argparse._SubParsersAction, name: str, **kwargs: object) -> argparse.ArgumentParser:
    parser = sub.add_parser(name, **kwargs)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="jat", description=__doc__)
    parser.add_argument("--db", help="database path (overrides $JAT_DB and the default)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="create the database and migrate to head")
    commands.add_parser("db-path", help="print the resolved database path and schema version")

    imp = commands.add_parser("import", help="bulk-load a job_app_tracker.csv export")
    imp.add_argument("csv_path")
    imp.add_argument("--force", action="store_true", help="import even if applications exist")

    company = commands.add_parser("company", help="manage companies").add_subparsers(dest="action", required=True)
    company_add = company.add_parser("add")
    company_add.add_argument("name")
    company_add.add_argument("--website")
    company_add.add_argument("--notes")
    _read_parser(company, "list")

    role = commands.add_parser("role", help="manage job postings").add_subparsers(dest="action", required=True)
    role_add = role.add_parser("add")
    role_add.add_argument("--company", required=True)
    role_add.add_argument("--title", required=True)
    role_add.add_argument("--location")
    role_add.add_argument("--arrangement", choices=enums.ARRANGEMENTS)
    role_add.add_argument("--comp-min", type=int)
    role_add.add_argument("--comp-max", type=int)
    role_add.add_argument("--url")
    role_add.add_argument("--jd-text")
    role_add.add_argument("--notes")
    role_list = _read_parser(role, "list")
    role_list.add_argument("--company")

    apply = commands.add_parser("apply", help="create an application for a role")
    apply.add_argument("--role-id", type=int, required=True)
    apply.add_argument("--source", choices=enums.SOURCES)
    apply.add_argument("--resume")
    apply.add_argument("--interest", choices=enums.INTERESTS)
    apply.add_argument("--note")

    app = commands.add_parser("app", help="manage applications").add_subparsers(dest="action", required=True)
    app_list = _read_parser(app, "list")
    app_list.add_argument("--status", choices=enums.STATUSES)
    app_list.add_argument("--company")
    app_show = _read_parser(app, "show")
    app_show.add_argument("id", type=int)
    app_status = app.add_parser("status")
    app_status.add_argument("id", type=int)
    app_status.add_argument("status", choices=enums.STATUSES)
    app_status.add_argument("--note")
    app_status.add_argument("--at")
    app_interest = app.add_parser("interest")
    app_interest.add_argument("id", type=int)
    app_interest.add_argument("interest", choices=enums.INTERESTS)
    app_note = app.add_parser("note")
    app_note.add_argument("id", type=int)
    app_note.add_argument("text")

    contact = commands.add_parser("contact", help="manage contacts").add_subparsers(dest="action", required=True)
    contact_add = contact.add_parser("add")
    contact_add.add_argument("--name", required=True)
    contact_add.add_argument("--company")
    contact_add.add_argument("--title")
    contact_add.add_argument("--email")
    contact_add.add_argument("--phone")
    contact_add.add_argument("--linkedin")
    contact_add.add_argument("--notes")
    contact_list = _read_parser(contact, "list")
    contact_list.add_argument("--company")
    contact_link = contact.add_parser("link")
    contact_link.add_argument("app_id", type=int)
    contact_link.add_argument("contact_id", type=int)
    contact_link.add_argument("--as", dest="relationship", choices=enums.RELATIONSHIPS, required=True)

    interview = commands.add_parser("interview", help="manage interviews").add_subparsers(dest="action", required=True)
    interview_add = interview.add_parser("add")
    interview_add.add_argument("app_id", type=int)
    interview_add.add_argument("--kind", choices=enums.INTERVIEW_KINDS, required=True)
    interview_add.add_argument("--at", dest="scheduled_at")
    interview_add.add_argument("--duration", dest="duration_min", type=int)
    interview_add.add_argument("--location")
    interview_add.add_argument("--with", dest="contact_id", type=int)
    interview_add.add_argument("--prep")
    interview_outcome = interview.add_parser("outcome")
    interview_outcome.add_argument("interview_id", type=int)
    interview_outcome.add_argument("outcome", choices=enums.INTERVIEW_OUTCOMES)
    interview_outcome.add_argument("--debrief")
    interview_list = _read_parser(interview, "list")
    interview_list.add_argument("--app", dest="app_id", type=int)
    interview_list.add_argument("--upcoming", action="store_true")

    _read_parser(commands, "pipeline", help="show applications grouped by status")
    return parser


def _rows(items: Sequence[object], fields: Sequence[str]) -> list[list[object]]:
    return [[getattr(item, field) for field in fields] for item in items]


def _render(items: Sequence[object], fields: Sequence[str], json_output: bool) -> str:
    if json_output:
        return format.as_json(items)
    return format.table(_rows(items, fields), fields)


def _detail_text(detail: object) -> str:
    sections = [
        format.table(
            _rows([detail.application], ("id", "role_id", "status", "interest", "applied_at", "notes")),
            ("id", "role_id", "status", "interest", "applied_at", "notes"),
        ),
        format.table(_rows([detail.company], ("id", "name", "website")), ("id", "name", "website")),
        format.table(
            _rows([detail.role], ("id", "title", "location", "arrangement", "url")),
            ("id", "title", "location", "arrangement", "url"),
        ),
        format.table(
            _rows(detail.timeline, ("status", "occurred_at", "note")),
            ("status", "occurred_at", "note"),
        ),
        format.table(
            [
                [contact.id, contact.name, contact.title, relationship]
                for contact, relationship in detail.contacts
            ],
            ("id", "name", "title", "relationship"),
        ),
        format.table(
            _rows(detail.interviews, ("id", "kind", "scheduled_at", "outcome")),
            ("id", "kind", "scheduled_at", "outcome"),
        ),
    ]
    return "\n\n".join(sections)


def _pipeline_text(board: dict[str, list[object]]) -> str:
    sections = []
    for status in enums.STATUSES:
        applications = board.get(status, [])
        if applications:
            body = format.table(
                _rows(applications, ("id", "role_id", "interest", "applied_at")),
                ("id", "role_id", "interest", "applied_at"),
            )
            sections.append(f"{status} ({len(applications)})\n{body}")
    return "\n\n".join(sections) if sections else "No applications."


def _database_path(raw: str | None) -> Path:
    return Path(raw).expanduser() if raw is not None else db.default_db_path()


# Errors that mean the user asked for something impossible, not that the tool is
# broken. They print one stderr line and exit 1; everything else keeps its
# traceback.
_USER_ERRORS = (ValueError, sqlite3.IntegrityError, FileNotFoundError, importer.ImportBlocked)


def _user_error_message(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return f"cannot read {exc.filename}: {(exc.strerror or 'no such file').lower()}"
    if isinstance(exc, sqlite3.IntegrityError):
        return f"database rejected the change: {exc}"
    return str(exc)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except _USER_ERRORS as exc:
        print(f"jat: error: {_user_error_message(exc)}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    path = _database_path(args.db)
    if args.command == "init":
        with Store.open(path):
            pass
        print(path)
        return 0
    if args.command == "db-path":
        if not path.exists():
            print(f"{path} (schema 0, not created)")
            return 0
        conn = db.connect(path)
        try:
            version = db.schema_version(conn)
        finally:
            conn.close()
        print(f"{path} (schema {version})")
        return 0
    with Store.open(path) as store:
        if args.command == "import":
            count = importer.import_csv(store, args.csv_path, force=args.force)
            print(f"Imported {count} applications.")
        elif args.command == "company":
            if args.action == "add":
                item = store.add_company(args.name, website=args.website, notes=args.notes)
                print(f"Company {item.id}: {item.name}")
            else:
                print(_render(store.companies(), ("id", "name", "website", "notes"), args.json))
        elif args.command == "role":
            if args.action == "add":
                item = store.add_role(
                    company=args.company, title=args.title, location=args.location,
                    arrangement=args.arrangement, comp_min=args.comp_min, comp_max=args.comp_max,
                    url=args.url, jd_text=args.jd_text, notes=args.notes,
                )
                print(f"Role {item.id}: {item.title}")
            else:
                items = store.roles(company=args.company)
                print(_render(items, ("id", "company_id", "title", "location", "arrangement", "url"), args.json))
        elif args.command == "apply":
            item = store.apply(
                role_id=args.role_id, source=args.source, resume_version=args.resume,
                interest=args.interest, note=args.note,
            )
            print(f"Application {item.id}: {item.status}")
        elif args.command == "app":
            if args.action == "list":
                items = store.applications(status=args.status, company=args.company)
                print(_render(items, ("id", "role_id", "status", "interest", "applied_at"), args.json))
            elif args.action == "show":
                detail = store.application_detail(args.id)
                print(format.as_json(detail) if args.json else _detail_text(detail))
            elif args.action == "status":
                item = store.record_status(args.id, args.status, note=args.note, occurred_at=args.at)
                print(f"Application {item.id}: {item.status}")
            elif args.action == "interest":
                item = store.set_interest(args.id, args.interest)
                print(f"Application {item.id}: interest {item.interest}")
            else:
                item = store.add_note(args.id, args.text)
                print(f"Application {item.id}: note added")
        elif args.command == "contact":
            if args.action == "add":
                item = store.add_contact(
                    args.name, company=args.company, title=args.title, email=args.email,
                    phone=args.phone, linkedin=args.linkedin, notes=args.notes,
                )
                print(f"Contact {item.id}: {item.name}")
            elif args.action == "list":
                items = store.contacts(company=args.company)
                print(_render(items, ("id", "company_id", "name", "title", "email", "phone"), args.json))
            else:
                store.link_contact(args.app_id, contact_id=args.contact_id, relationship=args.relationship)
                print(f"Linked contact {args.contact_id} to application {args.app_id}.")
        elif args.command == "interview":
            if args.action == "add":
                item = store.add_interview(
                    args.app_id, kind=args.kind, scheduled_at=args.scheduled_at,
                    duration_min=args.duration_min, location=args.location,
                    contact_id=args.contact_id, prep_notes=args.prep,
                )
                print(f"Interview {item.id}: {item.kind}")
            elif args.action == "outcome":
                item = store.set_interview_outcome(args.interview_id, args.outcome, debrief_notes=args.debrief)
                print(f"Interview {item.id}: {item.outcome}")
            else:
                items = store.interviews(app_id=args.app_id, upcoming=args.upcoming)
                fields = ("id", "application_id", "kind", "scheduled_at", "outcome")
                print(_render(items, fields, args.json))
        else:
            board = store.pipeline()
            print(format.as_json(board) if args.json else _pipeline_text(board))
    return 0
