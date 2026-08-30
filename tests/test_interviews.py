import unittest

from tests.helpers import fresh_store


@unittest.skip("pending: interview Store methods (build order step 7)")
class Interviews(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_add_and_read_back(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        iv = self.store.add_interview(app.id, kind="technical", scheduled_at="2026-09-03 14:00")
        self.assertEqual(iv.outcome, "pending")
        self.assertEqual([x.id for x in self.store.interviews(app_id=app.id)], [iv.id])

    def test_set_outcome_leaves_other_fields_alone(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        iv = self.store.add_interview(app.id, kind="onsite", scheduled_at="2026-09-10 09:00")
        updated = self.store.set_interview_outcome(iv.id, "passed", debrief_notes="strong")
        self.assertEqual(updated.outcome, "passed")
        self.assertEqual(updated.scheduled_at, iv.scheduled_at)
        self.assertEqual(updated.kind, iv.kind)


if __name__ == "__main__":
    unittest.main()
