CREATE TABLE application_status_events_new (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  status         TEXT NOT NULL CHECK (status IN (
                   'wishlist', 'applied', 'screen', 'interview',
                   'offer', 'rejected', 'accepted')),
  occurred_at    TEXT NOT NULL DEFAULT (datetime('now')),
  note           TEXT
);

INSERT INTO application_status_events_new
  (id, application_id, status, occurred_at, note)
SELECT id, application_id, status, occurred_at, note
FROM application_status_events;

DROP TABLE application_status_events;
ALTER TABLE application_status_events_new RENAME TO application_status_events;
CREATE INDEX idx_status_events_app ON application_status_events (application_id);
