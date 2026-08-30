import sqlite3
import unittest

from tests.helpers import fresh_store


@unittest.skip("pending: contact Store methods (build order step 6)")
class Contacts(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_link_contact_to_application(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        c = self.store.add_contact("Jane Doe", company="Acme")
        self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")
        contacts = self.store.application_detail(app.id).contacts
        self.assertEqual([(x.id, rel) for x, rel in contacts], [(c.id, "referrer")])

    def test_duplicate_link_is_rejected(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        c = self.store.add_contact("Jane Doe")
        self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")

    def test_unknown_relationship_is_rejected(self) -> None:
        app = self.store.apply(company="Acme", role="A")
        c = self.store.add_contact("Jane Doe")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.link_contact(app.id, contact_id=c.id, relationship="pen_pal")


if __name__ == "__main__":
    unittest.main()
