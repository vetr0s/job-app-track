"""argparse entry point. Each subcommand parses args, calls one Store method,
and hands the result to format. No SQL, no business logic here.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jat", description=__doc__)
    parser.add_argument("--db", help="database path (overrides $JAT_DB and the default)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the database and migrate to head")
    sub.add_parser("db-path", help="print the resolved database path and schema version")

    imp = sub.add_parser("import", help="bulk-load a job_app_tracker.csv export")
    imp.add_argument("csv_path")
    imp.add_argument("--force", action="store_true", help="import even if applications exist")

    # company / role / apply / app / contact / interview / pipeline subcommands
    # are added as their Store methods land.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _args = build_parser().parse_args(argv)
    raise NotImplementedError("command dispatch lands with the Store methods")
