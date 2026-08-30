"""Rendering for CLI output: plain-text tables and --json.

Kept apart from cli.py so the same renderers serve every subcommand and, later,
so the web frontend can reuse the JSON shaping.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any


def table(rows: Sequence[Sequence[Any]], headers: Sequence[str]) -> str:
    """Fixed-width columns via str.ljust. No third-party table library."""
    rendered_rows = [[str(value) for value in row] for row in rows]
    if any(len(row) != len(headers) for row in rendered_rows):
        raise ValueError("every row must have the same number of columns as headers")

    rendered_headers = [str(header) for header in headers]
    widths = [
        max([len(header), *(len(row[index]) for row in rendered_rows)])
        for index, header in enumerate(rendered_headers)
    ]

    def render(row: Sequence[str]) -> str:
        return "  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip()

    rule = "  ".join("-" * width for width in widths)
    lines = [render(rendered_headers), rule]
    lines.extend(render(row) for row in rendered_rows)
    return "\n".join(lines)


def as_json(obj: Any) -> str:
    """Serialize dataclasses and lists of them to an indented JSON string."""
    def default(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    return json.dumps(obj, default=default, indent=2)
