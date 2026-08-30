-- 0001_init.sql
-- Initial schema: companies, roles, applications with an append-only status
-- timeline, contacts with an application join, and interviews.
-- Enum columns are TEXT + CHECK; the canonical lists also live in core/enums.py.

CREATE TABLE companies (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  website     TEXT,
  notes       TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE roles (
  id           INTEGER PRIMARY KEY,
  company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  location     TEXT,
  arrangement  TEXT CHECK (arrangement IN ('onsite', 'hybrid', 'remote')),
  comp_min     INTEGER,
  comp_max     INTEGER,
  url          TEXT,
  jd_text      TEXT,
  notes        TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE applications (
  id             INTEGER PRIMARY KEY,
  role_id        INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  status         TEXT NOT NULL DEFAULT 'wishlist' CHECK (status IN (
                   'wishlist', 'applied', 'screen', 'interview',
                   'offer', 'rejected', 'accepted')),
  source         TEXT CHECK (source IN (
                   'board', 'referral', 'recruiter', 'cold', 'event', 'other')),
  resume_version TEXT,
  interest       TEXT CHECK (interest IN ('low', 'medium', 'high')),
  applied_at     TEXT,
  notes          TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE application_status_events (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  status         TEXT NOT NULL,
  occurred_at    TEXT NOT NULL DEFAULT (datetime('now')),
  note           TEXT
);

CREATE TABLE contacts (
  id          INTEGER PRIMARY KEY,
  company_id  INTEGER REFERENCES companies(id) ON DELETE SET NULL,
  name        TEXT NOT NULL,
  title       TEXT,
  email       TEXT,
  phone       TEXT,
  linkedin    TEXT,
  notes       TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE application_contacts (
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  contact_id     INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  relationship   TEXT NOT NULL CHECK (relationship IN (
                   'recruiter', 'referrer', 'interviewer', 'hiring_manager', 'other')),
  PRIMARY KEY (application_id, contact_id, relationship)
);

CREATE TABLE interviews (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  kind           TEXT CHECK (kind IN (
                   'phone_screen', 'technical', 'system_design',
                   'behavioral', 'onsite', 'hiring_manager', 'hr', 'other')),
  scheduled_at   TEXT,
  duration_min   INTEGER,
  location       TEXT,
  contact_id     INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
  outcome        TEXT NOT NULL DEFAULT 'pending' CHECK (outcome IN (
                   'pending', 'passed', 'failed', 'cancelled', 'no_decision')),
  prep_notes     TEXT,
  debrief_notes  TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_roles_company       ON roles (company_id);
CREATE INDEX idx_applications_role   ON applications (role_id);
CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_status_events_app   ON application_status_events (application_id);
CREATE INDEX idx_app_contacts_contact ON application_contacts (contact_id);
CREATE INDEX idx_interviews_app      ON interviews (application_id);
