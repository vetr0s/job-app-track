import unittest

from job_app_track import importer
from tests.helpers import fresh_store


class DateParsing(unittest.TestCase):
    def test_year_is_assumed_when_absent(self) -> None:
        self.assertEqual(importer.parse_date("7/3"), "2026-07-03")
        self.assertEqual(importer.parse_date("07/12"), "2026-07-12")

    def test_two_digit_year_is_honored(self) -> None:
        self.assertEqual(importer.parse_date("7/3/26"), "2026-07-03")

    def test_four_digit_year_is_honored(self) -> None:
        self.assertEqual(importer.parse_date("7/3/2025"), "2025-07-03")

    def test_blank_is_none(self) -> None:
        self.assertIsNone(importer.parse_date(""))

    def test_invalid_date_fails(self) -> None:
        with self.assertRaises(ValueError):
            importer.parse_date("2/30")


class ImportCsv(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_blank_status_becomes_wishlist(self) -> None:
        rows = "Position,Company,Location,Job Link,Applied?,Date Applied,Status,Interest Level,Notes\n"
        rows += "Dev,Acme,Remote,http://x,,,,,\n"
        path = self._write(rows)
        importer.import_csv(self.store, path)
        self.assertEqual(self.store.applications()[0].status, "wishlist")

    def test_preserves_fields_and_uses_applied_date_for_event(self) -> None:
        rows = self._header()
        rows += 'Dev,Acme,"Remote, WA",raw link,Yes,7/3/26,Applied,High," note "\n'
        importer.import_csv(self.store, self._write(rows))

        role = self.store.roles()[0]
        detail = self.store.application_detail(self.store.applications()[0].id)
        self.assertEqual(role.location, "Remote, WA")
        self.assertEqual(role.arrangement, "remote")
        self.assertEqual(role.url, "raw link")
        self.assertEqual(detail.application.applied_at, "2026-07-03")
        self.assertEqual(detail.application.notes, " note ")
        self.assertEqual(detail.timeline[0].occurred_at, "2026-07-03")

    def test_blank_position_uses_placeholder_and_blank_rows_are_skipped(self) -> None:
        rows = self._header() + ",Acme,Seattle,,,,,,\n,,,,,,,,\n"
        count = importer.import_csv(self.store, self._write(rows))
        self.assertEqual(count, 1)
        self.assertEqual(self.store.roles()[0].title, "(unspecified)")

    def test_unknown_status_fails_before_writing(self) -> None:
        rows = self._header() + "Dev,Acme,Remote,,,,Applied,,,\n"
        rows += "Dev,Beta,Remote,,,,Surprise,,,\n"
        with self.assertRaises(ValueError):
            importer.import_csv(self.store, self._write(rows))
        self.assertEqual(self.store.applications(), [])

    def test_unknown_interest_fails_loudly(self) -> None:
        rows = self._header() + "Dev,Acme,Remote,,,,Applied,Urgent,\n"
        with self.assertRaises(ValueError):
            importer.import_csv(self.store, self._write(rows))

    def test_refuses_when_applications_exist(self) -> None:
        role = self.store.add_role(company="Acme", title="A")
        self.store.apply(role_id=role.id)
        with self.assertRaises(RuntimeError):
            importer.import_csv(self.store, self._write(self._header()))

    @staticmethod
    def _header() -> str:
        return "Position,Company,Location,Job Link,Applied?,Date Applied,Status,Interest Level,Notes\n"

    def _write(self, text: str) -> str:
        import tempfile

        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(lambda: __import__("os").unlink(f.name))
        return f.name


if __name__ == "__main__":
    unittest.main()
