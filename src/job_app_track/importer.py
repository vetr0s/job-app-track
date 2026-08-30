"""One-shot import of the old spreadsheet (start-data/job_app_tracker.csv).

Per row: upsert a company by exact name, insert a role, insert an application,
write one status event. No contacts or interviews; the CSV has none. Refuses to
run against a database that already holds applications unless force is set.
The mapping is lossy on purpose, see docs/implementation-plan.html.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .core import Store

STATUS_FROM_CSV = {
    "": "wishlist",
    "applied": "applied",
    "technical exam screening": "screen",
    "interview scheduled": "interview",
    "interview completed": "interview",
    "rejected": "rejected",
    "offer": "offer",
    "accepted": "accepted",
}

INTEREST_FROM_CSV = {"": None, "high": "high", "medium": "medium", "low": "low"}

DEFAULT_YEAR = 2026
UNSPECIFIED_TITLE = "(unspecified)"


class ImportBlocked(Exception):
    """The target database already holds applications and force was not set."""
CSV_FIELDS = (
    "Position",
    "Company",
    "Location",
    "Job Link",
    "Applied?",
    "Date Applied",
    "Status",
    "Interest Level",
    "Notes",
)


@dataclass(frozen=True, slots=True)
class _ImportRow:
    company: str
    title: str
    location: str
    arrangement: str | None
    url: str
    status: str
    interest: str | None
    applied_at: str | None
    notes: str


def parse_date(raw: str) -> str | None:
    """Parse spreadsheet dates and assume DEFAULT_YEAR when absent."""
    value = raw.strip()
    if not value:
        return None

    parts = value.split("/")
    if len(parts) == 2:
        value = f"{value}/{DEFAULT_YEAR}"
        pattern = "%m/%d/%Y"
    elif len(parts) == 3 and len(parts[2]) == 2:
        pattern = "%m/%d/%y"
    elif len(parts) == 3:
        pattern = "%m/%d/%Y"
    else:
        raise ValueError(f"unsupported date: {raw!r}")
    return datetime.strptime(value, pattern).date().isoformat()


def arrangement_from_location(location: str) -> str | None:
    """'remote' or 'hybrid' substring wins, else None."""
    normalized = location.casefold()
    if "remote" in normalized:
        return "remote"
    if "hybrid" in normalized:
        return "hybrid"
    return None


def import_csv(store: Store, csv_path: str | Path, *, force: bool = False) -> int:
    """Load every row. Return the number of applications created."""
    rows = _read_rows(csv_path)
    with store.tx():
        if not force and store.applications():
            raise ImportBlocked("database already holds applications; pass --force to import anyway")
        for row in rows:
            store.add_company(row.company)
            role = store.add_role(
                company=row.company,
                title=row.title,
                location=row.location,
                arrangement=row.arrangement,
                url=row.url,
            )
            store.apply(
                role_id=role.id,
                status=row.status,
                interest=row.interest,
                applied_at=row.applied_at,
                notes=row.notes,
                occurred_at=row.applied_at,
            )
    return len(rows)


def _read_rows(csv_path: str | Path) -> list[_ImportRow]:
    parsed: list[_ImportRow] = []
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValueError("CSV header does not match the job tracker export")
        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                raise ValueError(f"row {line_number} has extra columns")
            if all(not value for value in raw_row.values()):
                continue
            company = raw_row["Company"].strip()
            if not company:
                raise ValueError(f"row {line_number} has no company")
            try:
                status = STATUS_FROM_CSV[raw_row["Status"].strip().casefold()]
                interest = INTEREST_FROM_CSV[raw_row["Interest Level"].strip().casefold()]
            except KeyError as error:
                raise ValueError(f"row {line_number} has an unknown mapping: {error.args[0]!r}") from error
            location = raw_row["Location"]
            parsed.append(
                _ImportRow(
                    company=company,
                    title=raw_row["Position"].strip() or UNSPECIFIED_TITLE,
                    location=location,
                    arrangement=arrangement_from_location(location),
                    url=raw_row["Job Link"],
                    status=status,
                    interest=interest,
                    applied_at=parse_date(raw_row["Date Applied"]),
                    notes=raw_row["Notes"],
                )
            )
    return parsed
