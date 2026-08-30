import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from job_app_track import cli
from job_app_track.core import db


class Parser(unittest.TestCase):
    def test_json_is_accepted_after_read_leaf(self) -> None:
        args = cli.build_parser().parse_args(["app", "list", "--json"])
        self.assertTrue(args.json)

    def test_apply_requires_explicit_role_id(self) -> None:
        args = cli.build_parser().parse_args(["apply", "--role-id", "42"])
        self.assertEqual(args.role_id, 42)

    def test_enum_choices_reject_unknown_status(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["app", "status", "1", "surprise"])

    def test_unknown_command_prints_full_help(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            cli.build_parser().parse_args(["bogus"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("Command-line frontend for the job application store", stderr.getvalue())

    def test_missing_subcommand_prints_that_commands_help(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["app"])
        text = stderr.getvalue()
        self.assertIn("{list,show,status,interest,note}", text)
        self.assertIn("positional arguments:", text)


class Dispatch(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db_path = str(Path(directory.name) / "jat.db")

    def run_cli(self, *args: str) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli.main(["--db", self.db_path, *args])
        self.assertEqual(result, 0)
        return output.getvalue().strip()

    def test_init_and_db_path(self) -> None:
        self.assertEqual(
            self.run_cli("db-path"),
            f"{self.db_path} (schema 0, not created)",
        )
        self.assertFalse(Path(self.db_path).exists())
        self.assertEqual(self.run_cli("init"), self.db_path)
        head = max(version for version, _ in db._migration_sql())
        self.assertEqual(self.run_cli("db-path"), f"{self.db_path} (schema {head})")

    def test_role_apply_and_json_list(self) -> None:
        self.assertEqual(
            self.run_cli("role", "add", "--company", "Acme", "--title", "Engineer"),
            "Role 1: Engineer",
        )
        self.assertEqual(self.run_cli("apply", "--role-id", "1"), "Application 1: applied")
        payload = json.loads(self.run_cli("app", "list", "--json"))
        self.assertEqual(payload[0]["role_id"], 1)
        self.assertEqual(payload[0]["status"], "applied")

    def test_contact_interview_and_pipeline(self) -> None:
        self.run_cli("role", "add", "--company", "Acme", "--title", "Engineer")
        self.run_cli("apply", "--role-id", "1")
        self.assertEqual(
            self.run_cli("contact", "add", "--name", "Jane", "--company", "Acme"),
            "Contact 1: Jane",
        )
        self.run_cli("contact", "link", "1", "1", "--as", "interviewer")
        self.assertEqual(
            self.run_cli("interview", "add", "1", "--kind", "technical"),
            "Interview 1: technical",
        )
        detail = self.run_cli("app", "show", "1")
        self.assertIn("interviewer", detail)
        self.assertIn("technical", detail)
        board = json.loads(self.run_cli("pipeline", "--json"))
        self.assertEqual(board["applied"][0]["id"], 1)


if __name__ == "__main__":
    unittest.main()
