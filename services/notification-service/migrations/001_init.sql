CREATE TABLE IF NOT EXISTS notification_log (
    id           UUID PRIMARY KEY,
    event_id     VARCHAR(128) NOT NULL UNIQUE,
    event_type   VARCHAR(64)  NOT NULL,
    channel      VARCHAR(32)  NOT NULL,
    body         TEXT,
    delivered_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    profile_id   UUID PRIMARY KEY,
    email_opt_in BOOLEAN NOT NULL DEFAULT TRUE,
    push_opt_in  BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_notif_event ON notification_log(event_id);
