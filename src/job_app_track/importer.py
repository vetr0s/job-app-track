"""One-shot import of the old spreadsheet (start-data/job_app_tracker.csv).

Per row: upsert a company by exact name, insert a role, insert an application,
write one status event. No contacts or interviews; the CSV has none. Refuses to
run against a database that already holds applications unless force is set.
The mapping is lossy on purpose, see docs/implementation-plan.html.
"""

from __future__ import annotations

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


def parse_date(raw: str) -> str | None:
    """M/D, M/D/YY, MM/DD -> YYYY-MM-DD. Assume DEFAULT_YEAR when absent. Blank -> None."""
    raise NotImplementedError


def arrangement_from_location(location: str) -> str | None:
    """'remote' or 'hybrid' substring wins, else None."""
    raise NotImplementedError


def import_csv(store: Store, csv_path: str | Path, *, force: bool = False) -> int:
    """Load every row. Return the number of applications created."""
    raise NotImplementedError
