CREATE TABLE IF NOT EXISTS payments (
    id                      UUID PRIMARY KEY,
    idempotency_key         VARCHAR(128) NOT NULL UNIQUE,
    debtor_profile_id       UUID NOT NULL,
    creditor_sort_code      VARCHAR(8)  NOT NULL,
    creditor_account_number VARCHAR(16) NOT NULL,
    creditor_name           VARCHAR(255),
    amount_minor            BIGINT NOT NULL CHECK (amount_minor > 0),
    currency                CHAR(3) NOT NULL DEFAULT 'GBP',
    reference               VARCHAR(255),
    state                   VARCHAR(32) NOT NULL DEFAULT 'pending',
    partner_reference       VARCHAR(128),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_attempts (
    id               UUID PRIMARY KEY,
    payment_id       UUID NOT NULL REFERENCES payments(id),
    attempt_no       INT  NOT NULL,
    partner_response TEXT,
    attempted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id           UUID PRIMARY KEY,
    payment_id   UUID NOT NULL REFERENCES payments(id),
    event_type   VARCHAR(64) NOT NULL,
    payload      JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payments_debtor  ON payments(debtor_profile_id);
CREATE INDEX IF NOT EXISTS idx_payments_state   ON payments(state);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON outbox_events(published_at) WHERE published_at IS NULL;
