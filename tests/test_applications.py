import unittest

from tests.helpers import fresh_store


@unittest.skip("pending: application Store methods (build order step 5)")
class Applications(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_apply_sets_status_and_writes_one_event(self) -> None:
        app = self.store.apply(company="Acme", role="Backend Engineer", source="referral")
        self.assertEqual(app.status, "applied")
        detail = self.store.application_detail(app.id)
        self.assertEqual([e.status for e in detail.timeline], ["applied"])

    def test_record_status_keeps_denorm_in_sync(self) -> None:
        app = self.store.apply(company="Acme", role="Backend Engineer")
        self.store.record_status(app.id, "screen", note="recruiter call")
        self.assertEqual(self.store.application_detail(app.id).application.status, "screen")

    def test_pipeline_groups_every_application_once(self) -> None:
        a = self.store.apply(company="Acme", role="A")
        b = self.store.apply(company="Beta", role="B")
        self.store.record_status(b.id, "interview")
        board = self.store.pipeline()
        seen = [app.id for apps in board.values() for app in apps]
        self.assertCountEqual(seen, [a.id, b.id])

    def test_tx_rolls_back_on_error(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        with self.assertRaises(ValueError):
            with self.store.tx():
                self.store.record_status(app.id, "offer")
                raise ValueError("boom")
        self.assertEqual(self.store.application_detail(app.id).application.status, "applied")


if __name__ == "__main__":
    unittest.main()
