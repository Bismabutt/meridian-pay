# Entity Relationship Design

Seven databases, one per service. No shared tables.

## Notation

**FK** means a foreign key enforced by PostgreSQL. These exist only within
one service's database.

**ext ref** means an identifier that originates in another service. It is
stored for correlation but the database cannot enforce it, and no query
joins across databases.

---

## auth_db

```
users
  id                  UUID        PK
  company_name        TEXT
  company_number      TEXT        UNIQUE
  email               TEXT        UNIQUE
  password_hash       TEXT
  status              TEXT        active | suspended | pending_kyc
  kyc_status          TEXT
  created_at          TIMESTAMPTZ

sessions
  id                  UUID        PK
  user_id             UUID        FK -> users.id
  token_hash          TEXT
  expires_at          TIMESTAMPTZ
  created_at          TIMESTAMPTZ

api_keys
  id                  UUID        PK
  user_id             UUID        FK -> users.id
  key_hash            TEXT
  label               TEXT
  last_used_at        TIMESTAMPTZ
  revoked_at          TIMESTAMPTZ
```

**Password hashes, not passwords.** Tokens and API keys are stored hashed as
well, so a database compromise does not yield usable credentials.

---

## account_db

```
business_profiles
  id                  UUID        PK
  business_id         UUID        ext ref -> auth_db.users.id
  trading_name        TEXT
  address_line_1      TEXT
  postcode            TEXT
  industry_code       TEXT

virtual_accounts
  id                  UUID        PK
  business_id         UUID        ext ref -> auth_db.users.id
  sort_code           TEXT
  account_number      TEXT        UNIQUE
  currency            TEXT
  status              TEXT
  created_at          TIMESTAMPTZ

balance_projections
  account_id          UUID        PK, FK -> virtual_accounts.id
  balance_minor       BIGINT
  currency            TEXT
  as_of               TIMESTAMPTZ
  ledger_sequence     BIGINT
```

**The virtual account is the customer facing account number.** Funds are not
physically separate; they sit in the pooled account at the partner bank. The
ledger records the split.

**balance_projections is not authoritative.** `as_of` and `ledger_sequence`
exist so a consumer can tell how stale the value is. Any operation that moves
money queries the ledger directly.

---

## payment_db

```
payments
  id                  UUID        PK
  idempotency_key     TEXT        UNIQUE NOT NULL
  from_account_id     UUID        ext ref -> account_db.virtual_accounts.id
  to_sort_code        TEXT
  to_account_number   TEXT
  to_name             TEXT
  amount_minor        BIGINT
  currency            TEXT
  status              TEXT        pending | submitted | cleared | failed
  reference           TEXT
  created_at          TIMESTAMPTZ
  cleared_at          TIMESTAMPTZ

payment_attempts
  id                  UUID        PK
  payment_id          UUID        FK -> payments.id
  attempt_number      INT
  partner_response    JSONB
  outcome             TEXT
  attempted_at        TIMESTAMPTZ

outbox_events
  id                  UUID        PK
  aggregate_id        UUID
  event_type          TEXT        payment.initiated | payment.cleared | payment.failed
  payload             JSONB
  published_at        TIMESTAMPTZ NULL
  created_at          TIMESTAMPTZ
```

**`idempotency_key UNIQUE NOT NULL` is the guarantee.** Redis is the fast
path; this constraint is what makes duplicate payment impossible.

**payment_attempts records every submission to the partner bank.** During an
outage a single payment accumulates several rows, which is the retry
behaviour made auditable.

**outbox_events is written in the same transaction as the payment.** A
separate process publishes to Kafka and sets `published_at`. Without this, a
crash between the database write and the Kafka publish would lose the event.

---

## ledger_db

```
ledger_entries
  id                  UUID        PK
  transaction_id      UUID        NOT NULL, indexed
  account_id          TEXT        NOT NULL, indexed
  direction           TEXT        debit | credit
  amount_minor        BIGINT      NOT NULL
  currency            TEXT
  reference           TEXT
  created_at          TIMESTAMPTZ NOT NULL

reconciliation_snapshots
  id                  UUID        PK
  taken_at            TIMESTAMPTZ
  ledger_total_minor  BIGINT
  partner_total_minor BIGINT
  variance_minor      BIGINT
  status              TEXT        matched | variance
```

**There is no balance column.** A balance is `SUM(amount_minor)` over an
account's entries, with debits negative. Storing a balance would create the
possibility of it disagreeing with the entries that produced it.

**Every movement is two rows** sharing one `transaction_id`, one debit and
one credit, summing to zero. A transaction whose legs do not balance is
rejected before insertion. This is an integrity control, not error handling.

**Append only.** No UPDATE, no DELETE. A correction is a new balancing
transaction, which preserves the history of what was believed and when.

**reconciliation_snapshots proves solvency.** A daily job asserts that the
sum of all customer balances equals the pooled balance held at the partner
bank. A non zero variance is a safeguarding incident.

---

## fraud_db

```
fraud_rules
  id                  UUID        PK
  name                TEXT
  rule_type           TEXT
  threshold           JSONB
  weight              INT
  enabled             BOOLEAN

fraud_scores
  id                  UUID        PK
  payment_id          UUID        ext ref -> payment_db.payments.id
  score               INT
  triggered_rules     JSONB
  scored_at           TIMESTAMPTZ

review_queue
  id                  UUID        PK
  fraud_score_id      UUID        FK -> fraud_scores.id
  status              TEXT        open | cleared | escalated
  assigned_to         TEXT
  resolved_at         TIMESTAMPTZ
```

**`payment_id` is an external reference.** fraud-service learns about
payments through Kafka events and never queries payment_db. That is what
keeps it outside the money zone.

---

## fx_db

```
fx_rates
  id                  UUID        PK
  base_currency       TEXT
  quote_currency      TEXT
  rate                NUMERIC(18,8)
  provider            TEXT
  fetched_at          TIMESTAMPTZ

fx_conversions
  id                  UUID        PK
  payment_id          UUID        ext ref -> payment_db.payments.id
  from_currency       TEXT
  to_currency         TEXT
  rate_used           NUMERIC(18,8)
  rate_fetched_at     TIMESTAMPTZ
  converted_at        TIMESTAMPTZ
```

**`rate_used` and `rate_fetched_at` are both recorded.** When a customer
disputes a conversion, the platform can show the exact rate applied and how
old it was.

---

## notif_db

```
notifications
  id                  UUID        PK
  business_id         UUID        ext ref -> auth_db.users.id
  channel             TEXT        email | in_app
  template            TEXT
  payload             JSONB
  status              TEXT        pending | sent | failed
  created_at          TIMESTAMPTZ

delivery_attempts
  id                  UUID        PK
  notification_id     UUID        FK -> notifications.id
  attempt_number      INT
  provider_response   JSONB
  attempted_at        TIMESTAMPTZ
```

---

## Rules applied throughout

**Money is stored as integers in minor units.** `amount_minor BIGINT` holds
pence. Floating point arithmetic introduces rounding error, which in a
financial ledger is unacceptable.

**Timestamps are TIMESTAMPTZ.** Timezone aware, stored in UTC.

**Identifiers are UUIDs.** Sequential integers leak volume information and
make identifiers guessable.

**Foreign keys are enforced only within a database.** Cross service
references are stored and validated by the application, never by a join.
