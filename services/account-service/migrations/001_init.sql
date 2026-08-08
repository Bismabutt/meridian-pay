CREATE TABLE IF NOT EXISTS business_profiles (
    id              UUID PRIMARY KEY,
    user_id         UUID NOT NULL,
    trading_name    VARCHAR(255) NOT NULL,
    address         TEXT,
    account_status  VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS virtual_accounts (
    id              UUID PRIMARY KEY,
    profile_id      UUID NOT NULL REFERENCES business_profiles(id),
    sort_code       VARCHAR(8)  NOT NULL,
    account_number  VARCHAR(16) NOT NULL UNIQUE,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS balance_projections (
    profile_id      UUID PRIMARY KEY REFERENCES business_profiles(id),
    available_minor BIGINT NOT NULL DEFAULT 0,
    last_event_id   UUID,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vaccounts_number ON virtual_accounts(account_number);
CREATE INDEX IF NOT EXISTS idx_profiles_user    ON business_profiles(user_id);
