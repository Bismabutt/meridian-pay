CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    company_number  VARCHAR(32)  NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'active',
    kyc_status      VARCHAR(32)  NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id),
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    id              UUID PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id),
    key_hash        VARCHAR(128) NOT NULL UNIQUE,
    rate_limit_tier VARCHAR(32)  NOT NULL DEFAULT 'standard',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email);
