"""Read models returned by Store. Frozen; write methods take keyword args."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Company:
    id: int
    name: str
    website: str | None
    notes: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class Role:
    id: int
    company_id: int
    company: str
    title: str
    location: str | None
    arrangement: str | None
    comp_min: int | None
    comp_max: int | None
    url: str | None
    jd_text: str | None
    notes: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class Application:
    id: int
    role_id: int
    company: str
    title: str
    status: str
    source: str | None
    resume_version: str | None
    interest: str | None
    applied_at: str | None
    notes: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StatusEvent:
    id: int
    application_id: int
    status: str
    occurred_at: str
    note: str | None


@dataclass(frozen=True, slots=True)
class Contact:
    id: int
    company_id: int | None
    name: str
    title: str | None
    email: str | None
    phone: str | None
    linkedin: str | None
    notes: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class Interview:
    id: int
    application_id: int
    kind: str | None
    scheduled_at: str | None
    duration_min: int | None
    location: str | None
    contact_id: int | None
    outcome: str
    prep_notes: str | None
    debrief_notes: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class ApplicationDetail:
    application: Application
    role: Role
    company: Company
    timeline: list[StatusEvent]
    contacts: list[tuple[Contact, str]]
    interviews: list[Interview]
