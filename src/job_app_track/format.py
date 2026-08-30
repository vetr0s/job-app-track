"""Rendering for CLI output: plain-text tables and --json.

Kept apart from cli.py so the same renderers serve every subcommand and, later,
so the web frontend can reuse the JSON shaping.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def table(rows: Sequence[Sequence[Any]], headers: Sequence[str]) -> str:
    """Fixed-width columns via str.ljust. No third-party table library."""
    raise NotImplementedError


def as_json(obj: Any) -> str:
    """Serialize dataclasses and lists of them to an indented JSON string."""
    raise NotImplementedError
