CREATE TABLE IF NOT EXISTS fx_rate_snapshots (
    id         UUID PRIMARY KEY,
    pair       VARCHAR(8)     NOT NULL,
    rate       NUMERIC(18,8)  NOT NULL,
    fetched_at TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversions (
    id              UUID PRIMARY KEY,
    pair            VARCHAR(8)    NOT NULL,
    mid_rate        NUMERIC(18,8) NOT NULL,
    effective_rate  NUMERIC(18,8) NOT NULL,
    amount_minor    BIGINT        NOT NULL,
    converted_minor BIGINT        NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rates_pair ON fx_rate_snapshots(pair, fetched_at DESC);
