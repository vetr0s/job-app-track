import unittest

from job_app_track import importer
from tests.helpers import fresh_store


@unittest.skip("pending: importer implementation (build order step 8)")
class DateParsing(unittest.TestCase):
    def test_year_is_assumed_when_absent(self) -> None:
        self.assertEqual(importer.parse_date("7/3"), "2026-07-03")
        self.assertEqual(importer.parse_date("07/12"), "2026-07-12")

    def test_two_digit_year_is_honored(self) -> None:
        self.assertEqual(importer.parse_date("7/3/26"), "2026-07-03")

    def test_blank_is_none(self) -> None:
        self.assertIsNone(importer.parse_date(""))


@unittest.skip("pending: importer implementation (build order step 8)")
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

    def test_refuses_when_applications_exist(self) -> None:
        self.store.apply(company="Acme", role="A")
        with self.assertRaises(RuntimeError):
            importer.import_csv(self.store, self._write("header only\n"))

    def _write(self, text: str) -> str:
        import tempfile

        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(lambda: __import__("os").unlink(f.name))
        return f.name


if __name__ == "__main__":
    unittest.main()
