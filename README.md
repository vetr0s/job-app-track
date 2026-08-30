# Job application tracker

A local CLI for tracking software engineering job applications in SQLite.
Runtime code uses only the Python standard library.

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

## Tests

```sh
uv run python -m unittest discover -s tests
```
