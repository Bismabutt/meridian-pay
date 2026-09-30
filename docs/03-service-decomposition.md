# Service Decomposition

Eight services, grouped into three criticality tiers. The tier determines
replica counts, autoscaling bounds, disruption budgets, rollout strategy and
database sizing.

## Criticality tiers

| Tier | Meaning | Services |
|---|---|---|
| **1** | Customer cannot move money without it | api-gateway, auth-service, payment-service, ledger-service |
| **2** | Degrades the product but money still moves | account-service, fraud-service, fx-service |
| **3** | Explicitly permitted to lag | notification-service |

---

## The services

### api-gateway — Tier 1

**Owns:** nothing. Holds no database.

**Responsibilities:** JWT validation, rate limiting, request routing.

**Why it owns no data:** a gateway that stores state becomes a bottleneck and
a single point of failure. It validates and routes, nothing more.

**Scaling:** 4 replicas minimum, 20 maximum. Sees every request, so it scales
first and furthest.

---

### auth-service — Tier 1

**Owns:** `users`, `sessions`, `api_keys` in `auth_db`.

**Responsibilities:** registration, login, JWT issuance, API key management.

**Tier 1 for login only.** A customer who cannot log in cannot move money.
Registration failures are less severe.

**External dependency:** identity provider for KYC. Failure delays
onboarding, never blocks existing users.

---

### account-service — Tier 2, highest read volume

**Owns:** `business_profiles`, `virtual_accounts`, `balance_projections` in
`account_db`.

**Responsibilities:** account creation, profile management, balance reads.

**The balance projection is not authoritative.** It is a cached view for
display. Any operation that moves money queries the ledger directly.

**Why Tier 2 but the most aggressive scaling:** at roughly 3,000 reads per
second against 500 payments, this service carries the highest request volume
in the platform. Criticality and load are different axes.

---

### payment-service — Tier 1, money zone

**Owns:** `payments`, `payment_attempts`, `outbox_events` in `payment_db`.

**Responsibilities:** payment orchestration, idempotency enforcement, partner
bank submission, retry handling.

**The most complex service.** It coordinates the ledger write, the partner
submission, and the event publication, and it must leave the system
consistent if any of those fail.

**Rollout strategy:** `maxUnavailable: 0`. Capacity never drops during a
deployment.

**Termination grace period:** 60 seconds, so in flight payments complete
before the pod exits.

---

### ledger-service — Tier 1, money zone, highest value

**Owns:** `ledger_entries`, `reconciliation_snapshots` in `ledger_db`.

**Responsibilities:** double entry writes, balance derivation, daily
reconciliation against the partner pooled balance.

**Written in Go rather than Python.** Predictable latency and a compiled
binary with no runtime dependencies matter more here than development speed.

**Design constraints:**

- Append only. Entries are never updated or deleted.
- No balance column. A balance is the sum of entries, derived on read.
- Every movement is two legs, debit and credit, sharing one transaction id,
  summing to zero. A transaction that does not balance is rejected before it
  reaches the database.
- Amounts are integers in minor units. Never floating point.

**Scaling:** vertical before horizontal. Write correctness outranks
throughput, so the autoscaler is deliberately conservative: maximum 6
replicas against payment-service's 14.

---

### fraud-service — Tier 2

**Owns:** `fraud_rules`, `fraud_scores`, `review_queue` in `fraud_db`.

**Responsibilities:** rule based scoring of payments, flagging for review.

**Consumes Kafka events. Never reads payment_db or ledger_db directly.**

This is the key isolation decision: fraud analysis sits outside the money
zone entirely. It receives what it needs through events rather than being
granted access to the money zone's data.

---

### fx-service — Tier 2

**Owns:** `fx_rates`, `fx_conversions` in `fx_db`.

**Responsibilities:** currency conversion, rate caching.

**Low request volume, served mostly from cache.** The smallest resource
allocation in the platform.

**On provider failure:** serve stale rates with a visible age rather than
failing the conversion.

---

### notification-service — Tier 3

**Owns:** `notifications`, `delivery_attempts` in `notif_db`.

**Responsibilities:** email and in app notifications.

**Explicitly permitted to lag.** A delayed payment confirmation email is an
inconvenience. A delayed payment is not.

**CPU limit set deliberately.** This is the only service with a CPU ceiling,
so that under contention it cannot starve the money path.

**No PodDisruptionBudget.** Tier 3 may be fully unavailable during a node
drain.

---

## Data ownership rules

**One service, one database. No shared tables.**

**Foreign keys exist only within a single service's database.** A service
never has a foreign key into another service's data.

**Cross service identifiers are stored but never joined.** account-service
stores a `business_id` that originates in auth-service, but the database
cannot and does not enforce that relationship. The application does.

**Why:** a shared table creates a deployment dependency. Changing its schema
requires coordinating every service that reads it, which is the coupling
microservices exist to remove.

---

## Four patterns for cross service data

| Pattern | When used | Example |
|---|---|---|
| Synchronous call | The caller cannot proceed without the answer | payment-service asks ledger-service to write |
| Event | The consumer needs to know, but not immediately | fraud-service consumes payment.initiated |
| Local projection | Read heavy, staleness tolerable | account-service holds a balance projection for display |
| Shared identifier | Correlation only, no join | business_id appears in several databases |

---

## Scaling profiles

| Service | Replicas | Max | HPA target | PDB minAvailable |
|---|---|---|---|---|
| api-gateway | 4 | 20 | 65% | 3 |
| auth-service | 3 | 12 | 65% | 2 |
| account-service | 6 | 20 | 65% | 4 |
| payment-service | 3 | 14 | 65% | 2 |
| ledger-service | 3 | 6 | 70% | 2 |
| fraud-service | 2 | 8 | 70% | 1 |
| fx-service | 2 | 4 | 75% | 1 |
| notification-service | 2 | 6 | 80% | none |

**Why 65% for Tier 1:** scaling is not instantaneous. Metrics scrape
interval, HPA evaluation, pod start and node provisioning all add delay. A
higher target means customers experience the spike before capacity arrives.

**Why 80% for notification-service:** it is permitted to lag, so running it
hotter before scaling is a deliberate cost decision.
