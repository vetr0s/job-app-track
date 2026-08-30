import unittest

from tests.helpers import fresh_store


class Applications(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_apply_sets_status_and_writes_one_event(self) -> None:
        role = self.store.add_role(company="Acme", title="Backend Engineer")
        app = self.store.apply(role_id=role.id, source="referral")
        self.assertEqual(app.status, "applied")
        detail = self.store.application_detail(app.id)
        self.assertEqual([e.status for e in detail.timeline], ["applied"])

    def test_record_status_keeps_denorm_in_sync(self) -> None:
        role = self.store.add_role(company="Acme", title="Backend Engineer")
        app = self.store.apply(role_id=role.id)
        self.store.record_status(app.id, "screen", note="recruiter call")
        self.assertEqual(self.store.application_detail(app.id).application.status, "screen")

    def test_pipeline_groups_every_application_once(self) -> None:
        a = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        b = self.store.apply(role_id=self.store.add_role(company="Beta", title="B").id)
        self.store.record_status(b.id, "interview")
        board = self.store.pipeline()
        seen = [app.id for apps in board.values() for app in apps]
        self.assertCountEqual(seen, [a.id, b.id])

    def test_tx_rolls_back_on_error(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        with self.assertRaises(ValueError):
            with self.store.tx():
                self.store.record_status(app.id, "offer")
                raise ValueError("boom")
        self.assertEqual(self.store.application_detail(app.id).application.status, "applied")

    def test_duplicate_role_titles_keep_distinct_identity(self) -> None:
        first = self.store.add_role(company="Acme", title="Engineer", url="https://one")
        second = self.store.add_role(company="Acme", title="Engineer", url="https://two")
        app = self.store.apply(role_id=second.id)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(app.role_id, second.id)

    def test_unknown_write_fields_fail_before_sql(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_company("Acme", typo="value")
        with self.assertRaises(ValueError):
            self.store.add_role(company="Acme", title="Engineer", typo="value")

    def test_backdated_event_does_not_replace_latest_status(self) -> None:
        role = self.store.add_role(company="Acme", title="Engineer")
        app = self.store.apply(role_id=role.id, occurred_at="2026-08-20 10:00:00")
        self.store.record_status(app.id, "interview", occurred_at="2026-08-25 10:00:00")
        updated = self.store.record_status(app.id, "screen", occurred_at="2026-08-21 10:00:00")
        detail = self.store.application_detail(app.id)
        self.assertEqual(updated.status, "interview")
        self.assertEqual(detail.application.status, detail.timeline[-1].status)


if __name__ == "__main__":
    unittest.main()
