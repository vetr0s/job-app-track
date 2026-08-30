"""Connection setup, database path resolution, and the migration runner.

Migrations are numbered SQL files under migrations/. On connect the runner reads
PRAGMA user_version, applies every file with a higher number in its own
transaction, and sets user_version to that number.
"""

from __future__ import annotations

import os
import re
import sqlite3
from importlib import resources
from pathlib import Path

APP_DIR_NAME = "job-app-track"
DB_FILE_NAME = "jat.db"
MIGRATION_NAME = re.compile(r"^(\d{4})_[A-Za-z0-9][A-Za-z0-9_-]*\.sql$")


def default_db_path() -> Path:
    """$JAT_DB if set, else ~/.local/share/job-app-track/jat.db."""
    env = os.environ.get("JAT_DB")
    if env:
        return Path(env).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    return Path(data_home).expanduser() / APP_DIR_NAME / DB_FILE_NAME


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys on and Row rows. Does not migrate."""
    path = str(db_path)
    if path != ":memory:":
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        path = str(Path(path).expanduser())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply every pending migration file, each in its own transaction."""
    if conn.in_transaction:
        raise RuntimeError("cannot migrate inside a transaction")

    have = schema_version(conn)
    for version, sql in _migration_sql():
        if version <= have:
            continue
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{sql}\n"
            f"PRAGMA user_version = {version};\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        have = version


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _migration_sql() -> list[tuple[int, str]]:
    """(version, sql) for each migrations/NNNN_*.sql, ascending by version."""
    out: list[tuple[int, str]] = []
    versions: set[int] = set()
    for entry in resources.files("job_app_track.migrations").iterdir():
        if not entry.name.endswith(".sql"):
            continue
        match = MIGRATION_NAME.fullmatch(entry.name)
        if match is None:
            raise ValueError(f"invalid migration filename: {entry.name}")
        version = int(match.group(1))
        if version == 0:
            raise ValueError(f"migration version must be positive: {entry.name}")
        if version in versions:
            raise ValueError(f"duplicate migration version: {version}")
        versions.add(version)
        out.append((version, entry.read_text("utf-8")))
    return sorted(out)
