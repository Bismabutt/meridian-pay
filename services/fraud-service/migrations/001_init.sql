CREATE TABLE IF NOT EXISTS fraud_scores (
    id         UUID PRIMARY KEY,
    payment_id UUID NOT NULL,
    account_id UUID NOT NULL,
    score      INT  NOT NULL CHECK (score BETWEEN 0 AND 100),
    rule_hits  JSONB,
    scored_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_cases (
    id          UUID PRIMARY KEY,
    score_id    UUID NOT NULL REFERENCES fraud_scores(id),
    account_id  UUID NOT NULL,
    state       VARCHAR(32) NOT NULL DEFAULT 'open',
    reviewed_by VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account_baselines (
    account_id        UUID PRIMARY KEY,
    avg_amount_minor  BIGINT,
    payment_count     BIGINT DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scores_account ON fraud_scores(account_id, scored_at);
CREATE INDEX IF NOT EXISTS idx_cases_state    ON fraud_cases(state);
