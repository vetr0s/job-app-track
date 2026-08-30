# Manual testing guide

A hands-on walkthrough of the `jat` CLI. Every command surface is exercised at
least once. Run it against a throwaway database so your real data is untouched.

## Install the `jat` command

The project ships a `jat` entry point. Install it once so you do not type
`uv run` every time:

```sh
cd ~/source/repos/job-app-track
uv tool install --editable . --force
```

This puts `~/.local/bin/jat` on your PATH, symlinked into uv's tool store. The
install is editable, so source edits take effect with no reinstall.

- Update after a dependency change: `uv tool install --editable . --force`
- Remove it: `uv tool uninstall job-app-track`

If `uv run` warns about the cache, prefix commands with
`UV_CACHE_DIR=/tmp/job-app-track-uv-cache`.

## Point at a throwaway database

```sh
export JAT_DB=/tmp/jat-demo.db
rm -f "$JAT_DB"          # start clean each time you re-run this guide
```

`JAT_DB` saves you from repeating `--db` on every call. Path precedence is
`--db`, then `$JAT_DB`, then `~/.local/share/job-app-track/jat.db`.

## 1. Create the database

```sh
jat init
jat db-path        # should report schema 2
```

`jat db-path` never creates a file. A missing path reports schema 0.

## 2. Companies and roles

```sh
jat company add "Acme Corp" --website https://acme.example --notes "warm intro via Dana"
jat role add --company "Acme Corp" --title "Backend Engineer" --location Remote --arrangement remote --comp-min 150000 --comp-max 190000 --url https://acme.example/jobs/be
jat role add --company "Acme Corp" --title "Backend Engineer"   # same title, new ID
jat company list
jat role list
jat role list --company "Acme Corp"
```

The two "Backend Engineer" rows get different IDs. Postings are identified by
role ID, never by company plus title.

## 3. Apply to a role

Use an ID from `jat role list`.

```sh
jat apply --role-id 1 --source referral --interest high --note "referred by Dana"
jat app list
```

## 4. Walk an application through the pipeline

```sh
jat app status 1 screen --note "recruiter call, 30 min"
jat app status 1 interview --note "onsite loop booked"
jat app status 1 offer
jat app show 1
```

Backdated events stay in the timeline but do not replace a later cached status:

```sh
jat app status 1 applied --at 2026-01-01 --note "backfilled real apply date"
jat app show 1      # status still offer; timeline now has the 2026-01-01 row
```

## 5. Interest and notes

```sh
jat app interest 1 medium
jat app note 1 "comp band confirmed at top of range"
jat app show 1
```

## 6. Contacts

```sh
jat contact add --name "Dana Ruiz" --company "Acme Corp" --title "Eng Manager" --email dana@acme.example
jat contact list
jat contact link 1 1 --as referrer
jat app show 1      # the contact now appears in the detail
```

## 7. Interviews

```sh
jat interview add 1 --kind technical --at 2026-09-05T14:00 --duration 60 --location Zoom --with 1 --prep "review system design notes"
jat interview list
jat interview list --upcoming
jat interview outcome 1 passed --debrief "strong on API design"
jat interview list --app 1
```

## 8. Pipeline board

```sh
jat pipeline
```

## 9. JSON output

The `--json` flag goes after the leaf command.

```sh
jat app list --json
jat app show 1 --json
jat pipeline --json
jat interview list --upcoming --json
```

## 10. Seed CSV import

Use a fresh database. The importer validates the whole file before writing and
refuses to run when applications already exist.

```sh
export JAT_DB=/tmp/jat-seed.db
rm -f "$JAT_DB"
jat init
jat import start-data/job_app_tracker.csv
jat pipeline
jat import start-data/job_app_tracker.csv           # refuses: applications exist
jat import start-data/job_app_tracker.csv --force   # re-imports
```

The seed file yields 52 companies, 63 roles, 63 applications, 63 status events.
The import is lossy on purpose. Company name variants stay separate. Interview
Scheduled and Interview Completed both map to `interview`. Yearless dates use
2026.

## Invalid use prints help

Any misuse prints the full help for the command that failed and exits with
code 2.

```sh
jat bogus                          # full root help
jat app                            # full help for `app`
jat app status 1 --oops            # full help for `app status`
```

## Error handling

Expected errors print one `jat: error: ...` line to stderr and exit 1. Bad
flags and unknown subcommands print full help and exit 2. Unexpected failures
keep their traceback.

```sh
jat apply --role-id 999                        # jat: error: role 999 does not exist   (exit 1)
jat app show 42                                # jat: error: application 42 does not exist   (exit 1)
jat import /tmp/nope.csv                       # jat: error: cannot read ...: no such file   (exit 1)
jat apply --role-id 1 --source made-up-source  # full help, argparse rejects it   (exit 2)
```

## Web frontend

`jat serve` runs a local web frontend over the same database. Every CLI action
has a page or a form. Pages branch on the `HX-Request` header: a plain
navigation gets the full document, an htmx call gets the inner fragment for a
swap. User errors (`ValueError`, `LookupError`, `ImportBlocked`, constraint
violations) return the CLI's message with a 4xx code, wrapped in an alert
fragment for an htmx caller. See `docs/web-frontend-plan.html`.

```sh
export JAT_DB=/tmp/jat-seed.db          # reuse the seed database
jat serve --port 8791 &
```

Open `http://127.0.0.1:8791/` in a browser and click through:

- Pipeline board at `/`. Each card has a status `<select>` and a one-click
  Reject button; both post inline and morph the board in place. The Reject
  button disappears once the card is rejected.
- `/applications` lists rows. The filter form re-queries on change; the "Apply
  to a role" panel prepends a row.
- A row links to `/applications/<id>`: facts, timeline, and forms for status,
  interest, note, and linking a contact. Each form morphs the detail block.
- `/companies`, `/roles`, `/contacts`, `/interviews` each list rows with a
  filter form and an add panel. Interview rows carry an outcome form.
- `/import` takes a server-side path to a `job_app_tracker.csv` and reuses the
  CLI importer. It refuses a database that already holds applications unless
  "force" is checked.

Headless checks:

```sh
curl -s http://127.0.0.1:8791/applications | head -20                 # full page
curl -s -H "HX-Request: true" http://127.0.0.1:8791/applications      # fragment, no <!doctype>
curl -s -o /dev/null -w "%{http_code}\n" \
  -d "role_id=1&interest=high" http://127.0.0.1:8791/applications     # 303 to /applications
curl -s -H "HX-Request: true" -d "status=bogus" \
  http://127.0.0.1:8791/applications/1/status                        # <p class="error"> 400
kill %1
```

Ctrl-C stops the server.

## Cleanup

```sh
rm -f /tmp/jat-demo.db /tmp/jat-seed.db
unset JAT_DB
```

## Enum reference

- status: wishlist, applied, screen, interview, offer, rejected, accepted
- source: board, referral, recruiter, cold, event, other
- interest: low, medium, high
- arrangement: onsite, hybrid, remote
- relationship: recruiter, referrer, interviewer, hiring_manager, other
- interview kind: phone_screen, technical, system_design, behavioral, onsite,
  hiring_manager, hr, other
- interview outcome: pending, passed, failed, cancelled, no_decision
