import unittest

from job_app_track import cli
from job_app_track.web.http import Request, Response, Route, dispatch
from job_app_track.web.routes import ROUTES
from tests.helpers import fresh_store


def _dispatch(store, method, path, *, body=b"", htmx=False):
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


if __name__ == "__main__":
    unittest.main()
