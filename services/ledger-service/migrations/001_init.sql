-- The ledger is append-only. No UPDATE or DELETE is permitted against
-- ledger_entries. Corrections are written as new offsetting entries.

CREATE TABLE IF NOT EXISTS ledger_entries (
    id             UUID PRIMARY KEY,
    transaction_id UUID NOT NULL,
    account_id     VARCHAR(64) NOT NULL,
    direction      VARCHAR(6)  NOT NULL CHECK (direction IN ('debit','credit')),
    amount_minor   BIGINT      NOT NULL CHECK (amount_minor > 0),
    currency       CHAR(3)     NOT NULL DEFAULT 'GBP',
    payment_id     UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reconciliation_snapshots (
    id                    UUID PRIMARY KEY,
    as_of_date            DATE   NOT NULL,
    ledger_sum_minor      BIGINT NOT NULL,
    partner_balance_minor BIGINT NOT NULL,
    variance_minor        BIGINT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_account     ON ledger_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_transaction ON ledger_entries(transaction_id);
CREATE INDEX IF NOT EXISTS idx_ledger_created     ON ledger_entries(created_at);
