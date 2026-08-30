import sqlite3
import unittest

from job_app_track.core import db


@unittest.skip("pending: db.connect / db.migrate (build order step 2)")
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


if __name__ == "__main__":
    unittest.main()
