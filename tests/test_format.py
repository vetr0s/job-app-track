import unittest
from dataclasses import dataclass

from job_app_track import format


class TableFormatting(unittest.TestCase):
    def test_columns_expand_to_fit_values(self) -> None:
        rendered = format.table([["Ada", 7], ["Grace Hopper", 12]], ["Name", "Count"])
        self.assertEqual(
            rendered,
            "Name          Count\n------------  -----\nAda           7\nGrace Hopper  12",
        )

    def test_empty_table_keeps_header_and_rule(self) -> None:
        self.assertEqual(format.table([], ["Name"]), "Name\n----")

    def test_wrong_column_count_fails(self) -> None:
        with self.assertRaises(ValueError):
            format.table([["only one"]], ["One", "Two"])


class JsonFormatting(unittest.TestCase):
    def test_serializes_dataclasses_and_lists(self) -> None:
        @dataclass(frozen=True)
        class Item:
            name: str

        self.assertEqual(format.as_json([Item("Ada")]), '[\n  {\n    "name": "Ada"\n  }\n]')

    def test_unknown_types_fail_loudly(self) -> None:
        with self.assertRaises(TypeError):
            format.as_json(object())


if __name__ == "__main__":
    unittest.main()
