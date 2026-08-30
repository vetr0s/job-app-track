import sqlite3
import unittest

from tests.helpers import fresh_store


class Contacts(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_link_contact_to_application(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        c = self.store.add_contact("Jane Doe", company="Acme")
        self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")
        contacts = self.store.application_detail(app.id).contacts
        self.assertEqual([(x.id, rel) for x, rel in contacts], [(c.id, "referrer")])

    def test_duplicate_link_is_rejected(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        c = self.store.add_contact("Jane Doe")
        self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.link_contact(app.id, contact_id=c.id, relationship="referrer")

    def test_unknown_relationship_is_rejected(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        c = self.store.add_contact("Jane Doe")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.link_contact(app.id, contact_id=c.id, relationship="pen_pal")

    def test_contacts_are_ordered_by_name(self) -> None:
        second = self.store.add_contact("zoe")
        first = self.store.add_contact("Amy")
        self.assertEqual([contact.id for contact in self.store.contacts()], [first.id, second.id])

    def test_link_rejects_unknown_contact(self) -> None:
        app = self.store.apply(role_id=self.store.add_role(company="Acme", title="A").id)
        with self.assertRaises(ValueError):
            self.store.link_contact(app.id, contact_id=999, relationship="referrer")


if __name__ == "__main__":
    unittest.main()
