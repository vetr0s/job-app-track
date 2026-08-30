# Job application tracker

A local tracker for software engineering job applications, backed by SQLite.
A `jat` CLI and a `jat serve` web frontend are two frontends over the same
store. Jinja2 is the only runtime dependency; it is used by the web frontend.

## Setup

The project requires Python 3.13 and uses `uv` for its development environment.

```sh
uv sync
uv run jat init
```

The default database is `~/.local/share/job-app-track/jat.db`. Set `JAT_DB` or
pass `--db PATH` before the command to use another file.

## Basic workflow

Create a posting, then use its ID to create an application.

```sh
uv run jat role add --company "Acme Corp" --title "Backend Engineer"
uv run jat role list
uv run jat apply --role-id 1 --source referral --interest high
uv run jat app list
uv run jat app status 1 interview --note "Technical round scheduled"
uv run jat pipeline
```

Role IDs identify postings. A company can have several postings with the same
title.

Read commands accept `--json` after the leaf command.

```sh
uv run jat app list --json
uv run jat app show 1 --json
uv run jat interview list --upcoming --json
```

Run `uv run jat --help` for the full command list.

## Import the seed spreadsheet

The one-shot importer validates the whole CSV before writing. It refuses to
run when applications already exist unless `--force` is present.

```sh
uv run jat import start-data/job_app_tracker.csv
```

## Web frontend

`jat serve` runs a local web frontend over the same database. Every CLI action
has a page or a form.

```sh
uv run jat serve                       # http://127.0.0.1:8765
uv run jat serve --host 0.0.0.0 --port 9000
uv run jat --db /tmp/demo.db serve     # same --db / $JAT_DB resolution
```

The pipeline board is the landing page. Each card has an inline status dropdown
and a one-click Reject button. The list views carry filter forms and add
panels. `/import` takes a server-side path to a `job_app_tracker.csv`. The
server is single-connection and serves GET and POST only; run it on a trusted
network. Ctrl-C stops it.

## Tests

```sh
uv run python -m unittest discover -s tests
```
