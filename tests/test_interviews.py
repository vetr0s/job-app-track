import unittest

from tests.helpers import fresh_store


class Interviews(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_add_and_read_back(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        iv = self.store.add_interview(app.id, kind="technical", scheduled_at="2026-09-03 14:00")
        self.assertEqual(iv.outcome, "pending")
        self.assertEqual([x.id for x in self.store.interviews(app_id=app.id)], [iv.id])

    def test_set_outcome_leaves_other_fields_alone(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        iv = self.store.add_interview(app.id, kind="onsite", scheduled_at="2026-09-10 09:00")
        updated = self.store.set_interview_outcome(iv.id, "passed", debrief_notes="strong")
        self.assertEqual(updated.outcome, "passed")
        self.assertEqual(updated.scheduled_at, iv.scheduled_at)
        self.assertEqual(updated.kind, iv.kind)

    def test_upcoming_includes_only_pending_future_interviews(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        future = self.store.add_interview(app.id, kind="technical", scheduled_at="2999-01-01 09:00")
        completed = self.store.add_interview(app.id, kind="technical", scheduled_at="2999-01-02 09:00")
        self.store.set_interview_outcome(completed.id, "passed")
        self.store.add_interview(app.id, kind="technical", scheduled_at="2000-01-01 09:00")
        self.assertEqual([item.id for item in self.store.interviews(upcoming=True)], [future.id])

    def test_set_outcome_rejects_unknown_interview(self) -> None:
        with self.assertRaises(ValueError):
            self.store.set_interview_outcome(999, "passed")


if __name__ == "__main__":
    unittest.main()
