import sqlite3
import unittest
from unittest import mock

from job_app_track.core import db


class MigrationRunner(unittest.TestCase):
    def test_empty_database_reaches_head(self) -> None:
        conn = db.connect(":memory:")
        db.migrate(conn)
        head = max(v for v, _ in db._migration_sql())
        self.assertEqual(db.schema_version(conn), head)

    def test_rerun_is_a_noop(self) -> None:
        conn = db.connect(":memory:")
        db.migrate(conn)
        before = db.schema_version(conn)
        db.migrate(conn)
        self.assertEqual(db.schema_version(conn), before)

    def test_foreign_keys_are_enforced(self) -> None:
        conn = db.connect(":memory:")
        db.migrate(conn)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO roles (company_id, title) VALUES (999, 'x')")
            conn.commit()

    def test_failed_migration_is_atomic(self) -> None:
        conn = db.connect(":memory:")
        sql = "CREATE TABLE leaked (id INTEGER); INSERT INTO missing VALUES (1);"
        with mock.patch.object(db, "_migration_sql", return_value=[(1, sql)]):
            with self.assertRaises(sqlite3.OperationalError):
                db.migrate(conn)

        leaked = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'leaked'"
        ).fetchone()
        self.assertIsNone(leaked)
        self.assertEqual(db.schema_version(conn), 0)


if __name__ == "__main__":
    unittest.main()
