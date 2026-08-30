# job-app-track handoff

Handoff for the next agent. Tracked in git via a `!/_audit.md` exception to the
root `/_*` ignore rule. `notes/manual-testing.md` is tracked too; other
underscore-prefixed root files stay local.

Current commit: `22d471f` (`Bring the docs up to date with the finished web frontend`).
Worktree clean. Remote `origin` is `git@github.com:vetr0s/job-app-track.git`;
`main` is pushed and tracking `origin/main`.
Date: 2026-08-29.

## Bottom line

The CLI and the web frontend are both implemented. The Store, migrations,
domain modules, formatter, importer, full CLI command surface, and every web
route work. 101 tests pass. A real temporary database accepted the 63-row seed
import. The built wheel contains both SQL migrations, all web templates, and the
vendored htmx file.

The `docs/` plans are historical rationale. Current behavior lives in
`README.md`, `jat --help`, the Store signatures, the templates, and the tests.

## Product shape

This is a single-user job application tracker.

- Python 3.13.
- SQLite.
- No runtime dependencies.
- Stdlib `unittest`.
- `uv` manages the environment.
- `jat` is the installed command.
- `jat serve` runs a local web frontend over the same Store, with Jinja2 the
  one runtime dependency.

The database path precedence is `--db`, then `JAT_DB`, then
`~/.local/share/job-app-track/jat.db`.

`jat db-path` is read-only. A missing path prints schema zero and does not
create a file. `jat init` creates and migrates the database.

## Architecture

`job_app_track.core.Store` owns one SQLite connection. Frontends call Store
methods and never receive the connection.

Private concern modules own SQL:

```text
core/_companies.py
core/_applications.py
core/_contacts.py
core/_interviews.py
```

Frozen dataclasses in `core/models.py` are the read contract.

Every Store write opens `store.tx()`. The transaction context uses unique
SQLite savepoints. A write works alone and also composes inside an outer
`store.tx()`. An exception escaping the outer context rolls back every nested
write.

A role row is one posting. `Role.id` is its identity. Company plus title is
not unique. `Store.apply()` and `jat apply` require a role ID.

`applications.status` caches the latest chronological status event.
Backdated events remain in the timeline but do not replace a later cached
status.

## Migration rules

Migrations are packaged SQL files named `NNNN_name.sql`.

`core/db.py` validates filenames and unique positive versions. It separates
each file into complete SQLite statements. It rejects transaction-control
statements. The runner owns `BEGIN IMMEDIATE`, the schema statements,
`PRAGMA user_version`, commit, and rollback.

Never edit a shipped migration.

- `0001_init.sql` creates the seven-table schema.
- `0002_status_event_check.sql` adds the status constraint to the timeline.

A new schema change needs `0003_*.sql`.

## Store contract

Important public calls:

```python
with Store.open(path) as store:
    company = store.add_company("Acme")
    role = store.add_role(company="Acme", title="Engineer")
    app = store.apply(role_id=role.id, source="referral")
    store.record_status(app.id, "screen", note="Recruiter call")
    detail = store.application_detail(app.id)

with store.tx():
    store.record_status(app.id, "offer")
    store.set_interest(app.id, "high")
```

`Store.apply()` also accepts `status`, `applied_at`, `notes`, and
`occurred_at`. The CSV importer uses these fields to create one application
and one matching initial event.

Unknown dynamic write fields raise `ValueError` before SQL construction.
Missing domain IDs raise `ValueError`. SQLite constraints raise
`sqlite3.IntegrityError`.

## CLI

The implemented top-level commands are:

```text
init
db-path
import
company
role
apply
app
contact
interview
pipeline
serve
```

Run `uv run jat --help` and each nested `--help` for exact flags.

Read commands own a trailing `--json` flag. Examples:

```sh
uv run jat role list --json
uv run jat app show 1 --json
uv run jat interview list --upcoming --json
uv run jat pipeline --json
```

Expected failures print one `jat: error: <message>` line to stderr and exit 1.
`main()` catches `ValueError`, `importer.ImportBlocked`, `sqlite3.IntegrityError`,
and a missing CSV file around `_run()`. Anything else keeps its traceback.

Invalid argparse use prints the full help for the command that failed, then the
error, then exits 2. This is the `_Parser` subclass in `cli.py`.

`app list`, `role list`, and `pipeline` show company and role names instead of
foreign keys. `Application` carries `company` and `title`; `Role` carries
`company`. JSON keeps the id fields and adds the names.

## Importer

`jat import start-data/job_app_tracker.csv` parses and validates the entire
file before writing.

The importer then opens one outer Store transaction. It creates one role per
CSV row and applies to the returned role ID. A database failure rolls back the
whole file. Existing applications block import unless `--force` is present.

The seed file produces:

```text
companies 52
roles 63
applications 63
application_status_events 63
```

The import is intentionally lossy. Company name variants stay separate.
Interview Scheduled and Interview Completed both map to `interview`.
Yearless dates use 2026.

## Tests and verification

Run:

```sh
UV_CACHE_DIR=/tmp/job-app-track-uv-cache \
  uv run python -m unittest discover -s tests -v
```

Result:

```text
Ran 102 tests in 0.5s
OK
```

The suite is clean under `-W error::ResourceWarning`. It covers migration
safety, nested rollback, explicit role identity, chronological status caching,
contacts, interviews, formatting, atomic import, every CLI dispatch branch, the
`jat: error:` path for each expected failure, full-help-on-misuse, and every web
route: read handlers both ways, each write handler, the board status change and
Reject button through `dispatch()`, htmx 4xx fragments, and `import_run`.

A real seed import created schema version 2 and 63 applications. JSON parsing
returned all 63 records.

The package build succeeded. The wheel contains both migration files, all
`web/templates/*.html`, and `web/static/*`. Hatchling may need network access
when it is absent from cache.

## Milestone commits

```text
19aa71a Record repository risks before implementation
6ffd699 Build the working Store foundation
3b1baf2 Expose the tracker through the CLI
8c1ecfd Protect database invariants
60a1640 Document the working CLI
d2f4f23 Show full help when a command is used wrong
09e2899 Turn expected failures into one-line CLI errors
6e99ae7 Cover the CLI branches that had only a manual sweep
989e8e9 Carry company and role names on read models
a95a2c2 Add the web frontend skeleton behind jat serve
de3539d Document the web frontend design and handoff
506af65 Fill in the web frontend handlers for CLI parity
7c8ced2 Add a one-click Reject button to each board card
879cc54 Close each web connection instead of keeping it alive
22d471f Bring the docs up to date with the finished web frontend
```

The audit report that drove the initial build is `docs/audit-2026-08-29.html`.
It describes the old scaffold. Use it as history, not current status.

## Install

`jat` is installed to `~/.local/bin` with `uv tool install --editable . --force`.
It is editable, so source edits take effect with no reinstall. The manual guide
is `notes/manual-testing.md`.

## Web frontend

`jat serve` runs a stdlib `http.server` bound to a route table, with Jinja2
templates and htmx 4.0.0 vendored at `web/static/htmx-4.0.0.min.js`. Single
connection, GET and POST only, same `--db` / `$JAT_DB` resolution as every
command. The design write-up is `docs/web-frontend-plan.html`; its route-table
"stub" markers are stale, every route is now live.

Every route in the plan's table is implemented and tested. Read handlers branch
on `req.is_htmx`: `page()` for a navigation, `fragment()` for a swap. Write
handlers call one Store method and return the matching read fragment for an
htmx caller or a 303 redirect for a plain form post. Templates live in
`web/templates/`; fragments carry a leading underscore and a stable root id
(`#board`, `#applications`, `#app-detail`, `#companies`, ...). Every enum
`<select>` is built from `core/enums.py` through `web/templates/_macros.html`.

htmx 4.0 interactions: inline status `<select>` and a one-click Reject button on
each board card post to `/applications/<id>/status` with `view=board` and morph
`#board`; filter forms re-query on change and morph the list; add panels morph
the list so a new row shows. The Reject button is hidden once an application is
already rejected. Nav counts via `<hx-partial>` were left out on purpose: not
CLI parity, and an out-of-band swap on every write is cross-cutting state for
little gain. Add it later if the nav needs badges.

`import_run` takes a server-side filesystem path in a text field and reuses
`importer.import_csv`; `dispatch()` still does not parse `multipart/form-data`.
A missing file is turned into a `ValueError` so it maps to 400.

Transport lives in `web/http.py` (`Request`, `Response`, `Route`, `dispatch`).
Handlers and the `ROUTES` table are in `web/routes.py`. `dispatch` maps
`ValueError` to 400, `LookupError` to 404, `ImportBlocked` to 409,
`sqlite3.IntegrityError` to 400; anything else is a 500 with a traceback. Same
split as `cli._USER_ERRORS`. `dispatch._fail` wraps the message in
`<p class="error">` for an htmx caller and returns plain text otherwise. Store
raises `ValueError` for a missing row, so a bad id is a 400, not a 404.

`render.page()` / `render.fragment()` take the HTTP status as `code=` so a
template context variable named `status` (the application filter) does not
collide with it.

`_Handler.protocol_version` is `HTTP/1.0`, not `HTTP/1.1`. The server is
single-threaded; an HTTP/1.1 keep-alive socket left idle by a browser blocked
`accept()` for every other connection and wedged the whole server. HTTP/1.0
closes each connection after one response. `tests/test_web.py::RunningServer`
drives the real socket server and guards this.

## Next useful work

Nothing is half-built. The CLI and the web frontend both have full parity, 102
tests pass, the wheel is complete, and `main` is pushed. Possible follow-ups,
none urgent: nav counts via `<hx-partial>`, a real `multipart/form-data` upload
for `import_run` instead of a server-side path, pagination on the list views,
and a browser-driven smoke test (most web tests exercise `dispatch()` directly;
only `RunningServer` touches a live socket).

## Commands

```sh
# Tests
UV_CACHE_DIR=/tmp/job-app-track-uv-cache \
  uv run python -m unittest discover -s tests -v

# Help
uv run jat --help

# Temporary database
uv run jat --db /tmp/jat-demo.db init
uv run jat --db /tmp/jat-demo.db role add \
  --company Acme --title Engineer
uv run jat --db /tmp/jat-demo.db apply --role-id 1
uv run jat --db /tmp/jat-demo.db app list --json

# Seed import
uv run jat --db /tmp/jat-seed.db import \
  start-data/job_app_tracker.csv

# Package
UV_CACHE_DIR=/tmp/job-app-track-uv-cache uv build
```

