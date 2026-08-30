"""Connection setup, database path resolution, and the migration runner.

Migrations are numbered SQL files under migrations/. On connect the runner reads
PRAGMA user_version, applies every file with a higher number in its own
transaction, and sets user_version to that number.
"""

from __future__ import annotations

import os
import sqlite3
from importlib import resources
from pathlib import Path

APP_DIR_NAME = "job-app-track"
DB_FILE_NAME = "jat.db"


def default_db_path() -> Path:
    """$JAT_DB if set, else ~/.local/share/job-app-track/jat.db."""
    env = os.environ.get("JAT_DB")
    if env:
        return Path(env).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    return Path(data_home).expanduser() / APP_DIR_NAME / DB_FILE_NAME


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys on and Row rows. Does not migrate."""
    raise NotImplementedError


def migrate(conn: sqlite3.Connection) -> None:
    """Apply every pending migration file, each in its own transaction."""
    raise NotImplementedError


def schema_version(conn: sqlite3.Connection) -> int:
    raise NotImplementedError


def _migration_sql() -> list[tuple[int, str]]:
    """(version, sql) for each migrations/NNNN_*.sql, ascending by version."""
    out: list[tuple[int, str]] = []
    for entry in resources.files("job_app_track.migrations").iterdir():
        if entry.name.endswith(".sql"):
            version = int(entry.name.split("_", 1)[0])
            out.append((version, entry.read_text("utf-8")))
    return sorted(out)
