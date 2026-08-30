"""Shared test fixtures."""

from __future__ import annotations

from job_app_track.core import Store


def fresh_store() -> Store:
    """A Store on a private in-memory database, migrated to head."""
    return Store.open(":memory:")
