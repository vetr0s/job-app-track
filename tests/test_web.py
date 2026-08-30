import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from job_app_track import cli
from job_app_track.importer import CSV_FIELDS
from job_app_track.web.http import Request, Response, Route, dispatch
from job_app_track.web.routes import ROUTES
from tests.helpers import fresh_store


def _dispatch(store, method, path, *, body=b"", form=None, htmx=False):
    if form is not None:
        body = urlencode(form).encode("utf-8")
    headers = {"HX-Request": "true"} if htmx else {}
    return dispatch(ROUTES, method, path, body=body, headers=headers, store=store)


class Dispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_unknown_path_is_404(self) -> None:
        self.assertEqual(_dispatch(self.store, "GET", "/nope").status, 404)

    def test_known_path_wrong_method_is_405(self) -> None:
        self.assertEqual(_dispatch(self.store, "POST", "/").status, 405)

    def test_path_parameters_are_captured_and_typed(self) -> None:
        seen: dict[str, str] = {}

        def handler(req: Request) -> Response:
            seen.update(req.params)
            return Response.text("ok", 200)

        routes = [Route("GET", "/applications/<int:id>", handler)]
        result = dispatch(routes, "GET", "/applications/7", body=b"", headers={}, store=self.store)
        self.assertEqual(result.status, 200)
        self.assertEqual(seen, {"id": "7"})

    def test_int_parameter_rejects_non_digits(self) -> None:
        routes = [Route("GET", "/applications/<int:id>", lambda r: Response.text("", 200))]
        result = dispatch(routes, "GET", "/applications/abc", body=b"", headers={}, store=self.store)
        self.assertEqual(result.status, 404)

    def test_handler_value_error_becomes_400(self) -> None:
        routes = [Route("GET", "/x", lambda r: (_ for _ in ()).throw(ValueError("bad input")))]
        result = dispatch(routes, "GET", "/x", body=b"", headers={}, store=self.store)
        self.assertEqual(result.status, 400)
        self.assertEqual(result.body, "bad input")

    def test_query_and_form_are_parsed(self) -> None:
        captured: dict[str, dict[str, str]] = {}

        def handler(req: Request) -> Response:
            captured["query"] = req.query
            captured["form"] = req.form
            return Response.text("", 200)

        routes = [Route("POST", "/x", handler)]
        dispatch(routes, "POST", "/x?a=1&a=2", body=b"b=3&c=four", headers={}, store=self.store)
        self.assertEqual(captured["query"], {"a": "1"})
        self.assertEqual(captured["form"], {"b": "3", "c": "four"})


class PipelineRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)
        role = self.store.add_role(company="Acme", title="Engineer")
        self.store.apply(role_id=role.id)

    def test_full_page_when_not_htmx(self) -> None:
        result = _dispatch(self.store, "GET", "/")
        self.assertEqual(result.status, 200)
        self.assertIn("<!doctype html>", result.body)
        self.assertIn("Acme", result.body)

    def test_fragment_only_when_htmx(self) -> None:
        result = _dispatch(self.store, "GET", "/", htmx=True)
        self.assertNotIn("<!doctype html>", result.body)
        self.assertIn('id="board"', result.body)

    def test_board_card_offers_a_reject_button(self) -> None:
        result = _dispatch(self.store, "GET", "/", htmx=True)
        self.assertIn(">Reject</button>", result.body)
        self.assertIn('"status": "rejected"', result.body)

    def test_reject_button_gone_once_rejected(self) -> None:
        [app] = self.store.applications()
        self.store.record_status(app.id, "rejected")
        result = _dispatch(self.store, "GET", "/", htmx=True)
        self.assertNotIn(">Reject</button>", result.body)


class StaticRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)

    def test_serves_css(self) -> None:
        result = _dispatch(self.store, "GET", "/static/app.css")
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "text/css")

    def test_serves_pinned_htmx(self) -> None:
        result = _dispatch(self.store, "GET", "/static/htmx-4.0.0.min.js")
        self.assertEqual(result.status, 200)
        self.assertIn('version="4.0.0', result.body)

    def test_rejects_path_traversal(self) -> None:
        self.assertEqual(_dispatch(self.store, "GET", "/static/..%2fsecret").status, 404)


class ServeCommand(unittest.TestCase):
    def test_parser_has_serve_with_defaults(self) -> None:
        args = cli.build_parser().parse_args(["serve"])
        self.assertEqual((args.host, args.port), ("127.0.0.1", 8765))

    def test_serve_accepts_host_and_port(self) -> None:
        args = cli.build_parser().parse_args(["serve", "--host", "0.0.0.0", "--port", "9001"])
        self.assertEqual((args.host, args.port), ("0.0.0.0", 9001))


class _Seeded(unittest.TestCase):
    """A store with one company, one role, and one applied application."""

    def setUp(self) -> None:
        self.store = fresh_store()
        self.addCleanup(self.store.close)
        self.role = self.store.add_role(company="Acme", title="Engineer")
        self.app = self.store.apply(role_id=self.role.id, interest="high")


class ReadHandlers(_Seeded):
    def test_application_index_page_lists_rows(self) -> None:
        result = _dispatch(self.store, "GET", "/applications")
        self.assertEqual(result.status, 200)
        self.assertIn("<!doctype html>", result.body)
        self.assertIn("Acme", result.body)

    def test_application_index_filters_by_status(self) -> None:
        other = self.store.add_role(company="Beta", title="SRE")
        self.store.apply(role_id=other.id, status="screen", occurred_at="2020-01-01")
        result = _dispatch(self.store, "GET", "/applications?status=screen", htmx=True)
        self.assertNotIn("<!doctype html>", result.body)
        self.assertIn('id="applications"', result.body)
        self.assertIn("Beta", result.body)
        self.assertNotIn("Acme", result.body)

    def test_application_show_fragment_for_htmx(self) -> None:
        result = _dispatch(self.store, "GET", f"/applications/{self.app.id}", htmx=True)
        self.assertNotIn("<!doctype html>", result.body)
        self.assertIn('id="app-detail"', result.body)
        self.assertIn("Engineer", result.body)

    def test_application_show_missing_id_is_400(self) -> None:
        self.assertEqual(_dispatch(self.store, "GET", "/applications/999").status, 400)

    def test_company_index(self) -> None:
        self.assertIn("Acme", _dispatch(self.store, "GET", "/companies").body)

    def test_role_index_filters_by_company(self) -> None:
        self.store.add_role(company="Beta", title="SRE")
        result = _dispatch(self.store, "GET", "/roles?company=Acme", htmx=True)
        self.assertIn("Engineer", result.body)
        self.assertNotIn("SRE", result.body)

    def test_contact_index(self) -> None:
        self.store.add_contact("Dana Lin", company="Acme")
        self.assertIn("Dana Lin", _dispatch(self.store, "GET", "/contacts").body)

    def test_interview_index(self) -> None:
        self.store.add_interview(self.app.id, kind="technical")
        result = _dispatch(self.store, "GET", "/interviews", htmx=True)
        self.assertIn('id="interviews"', result.body)
        self.assertIn("technical", result.body)

    def test_import_view_has_form(self) -> None:
        result = _dispatch(self.store, "GET", "/import")
        self.assertIn('name="csv_path"', result.body)


class WriteHandlers(_Seeded):
    def test_apply_redirects_and_creates(self) -> None:
        result = _dispatch(self.store, "POST", "/applications", form={"role_id": self.role.id})
        self.assertEqual(result.status, 303)
        self.assertEqual(result.headers["Location"], "/applications")
        self.assertEqual(len(self.store.applications()), 2)

    def test_apply_htmx_returns_list_fragment(self) -> None:
        result = _dispatch(
            self.store, "POST", "/applications", form={"role_id": self.role.id}, htmx=True
        )
        self.assertEqual(result.status, 200)
        self.assertIn('id="applications"', result.body)

    def test_interest_updates_application(self) -> None:
        _dispatch(self.store, "POST", f"/applications/{self.app.id}/interest", form={"interest": "low"})
        self.assertEqual(self.store.application_detail(self.app.id).application.interest, "low")

    def test_note_appends(self) -> None:
        _dispatch(self.store, "POST", f"/applications/{self.app.id}/note", form={"text": "rang back"})
        self.assertIn("rang back", self.store.application_detail(self.app.id).application.notes)

    def test_note_requires_text(self) -> None:
        result = _dispatch(
            self.store, "POST", f"/applications/{self.app.id}/note", form={"text": ""}, htmx=True
        )
        self.assertEqual(result.status, 400)
        self.assertTrue(result.body.startswith('<p class="error"'))

    def test_contact_link_shows_on_detail(self) -> None:
        contact = self.store.add_contact("Dana Lin")
        result = _dispatch(
            self.store,
            "POST",
            f"/applications/{self.app.id}/contacts",
            form={"contact_id": contact.id, "relationship": "referrer"},
            htmx=True,
        )
        self.assertIn("Dana Lin", result.body)
        self.assertIn("referrer", result.body)

    def test_company_create(self) -> None:
        result = _dispatch(self.store, "POST", "/companies", form={"name": "Globex"})
        self.assertEqual(result.status, 303)
        self.assertIn("Globex", {c.name for c in self.store.companies()})

    def test_company_create_requires_name(self) -> None:
        self.assertEqual(_dispatch(self.store, "POST", "/companies", form={"name": " "}).status, 400)

    def test_role_create(self) -> None:
        _dispatch(
            self.store,
            "POST",
            "/roles",
            form={"company": "Initech", "title": "Dev", "arrangement": "remote"},
        )
        titles = {r.title for r in self.store.roles(company="Initech")}
        self.assertEqual(titles, {"Dev"})

    def test_contact_create(self) -> None:
        _dispatch(self.store, "POST", "/contacts", form={"name": "Sam Ray", "company": "Acme"})
        self.assertIn("Sam Ray", {c.name for c in self.store.contacts()})

    def test_interview_create_and_outcome(self) -> None:
        _dispatch(
            self.store,
            "POST",
            "/interviews",
            form={"app_id": self.app.id, "kind": "technical", "scheduled_at": "2026-09-01 10:00"},
        )
        [interview] = self.store.interviews()
        result = _dispatch(
            self.store,
            "POST",
            f"/interviews/{interview.id}/outcome",
            form={"outcome": "passed"},
            htmx=True,
        )
        self.assertIn('id="interviews"', result.body)
        self.assertEqual(self.store.interviews()[0].outcome, "passed")


class StatusChangeThroughDispatch(_Seeded):
    def test_board_status_change_returns_board_fragment(self) -> None:
        result = _dispatch(
            self.store,
            "POST",
            f"/applications/{self.app.id}/status",
            form={"status": "screen", "view": "board"},
            htmx=True,
        )
        self.assertEqual(result.status, 200)
        self.assertNotIn("<!doctype html>", result.body)
        self.assertIn('id="board"', result.body)
        self.assertEqual(self.store.application_detail(self.app.id).application.status, "screen")

    def test_detail_status_change_returns_detail_fragment(self) -> None:
        result = _dispatch(
            self.store,
            "POST",
            f"/applications/{self.app.id}/status",
            form={"status": "offer"},
            htmx=True,
        )
        self.assertIn('id="app-detail"', result.body)
        self.assertNotIn('id="board"', result.body)

    def test_plain_post_redirects_to_detail(self) -> None:
        result = _dispatch(
            self.store, "POST", f"/applications/{self.app.id}/status", form={"status": "offer"}
        )
        self.assertEqual(result.status, 303)
        self.assertEqual(result.headers["Location"], f"/applications/{self.app.id}")


class ImportRun(_Seeded):
    def _csv(self) -> str:
        path = Path(tempfile.mkdtemp()) / "seed.csv"
        rows = [
            ",".join(CSV_FIELDS),
            "Engineer,NewCorp,Remote,http://x,y,01/02,applied,high,note",
        ]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self.addCleanup(path.unlink)
        return str(path)

    def test_import_run_loads_file_with_force(self) -> None:
        result = _dispatch(
            self.store, "POST", "/import", form={"csv_path": self._csv(), "force": "1"}
        )
        self.assertEqual(result.status, 200)
        self.assertIn("Imported 1", result.body)
        self.assertIn("NewCorp", {c.name for c in self.store.companies()})

    def test_import_run_missing_file_is_400(self) -> None:
        result = _dispatch(self.store, "POST", "/import", form={"csv_path": "/no/such.csv"})
        self.assertEqual(result.status, 400)


if __name__ == "__main__":
    unittest.main()
